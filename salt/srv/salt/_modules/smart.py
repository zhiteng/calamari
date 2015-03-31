from subprocess import PIPE, Popen
import salt.config
import salt.loader
import logging

log = logging.getLogger(__name__)
__opts__ = salt.config.minion_config('/etc/salt/minion')
__grains__ = salt.loader.grains(__opts__)

ARECA = 'areca'
MDADM = 'mdadm'


def _get_raid_devices():
    '''
    01:00.0 RAID bus controller: Areca Technology Corp. ARC-1680 8 port PCIe/PCI-X to SAS/SATA II RAID Controller
    '''
    raid_cmd = "lspci | /bin/grep -i raid | /bin/grep -v PATA | /usr/bin/head -1"
    p = Popen(raid_cmd, stdout=PIPE, stderr=PIPE, shell=True)
    stdout, stderr = p.communicate()
    return p.returncode, stdout, stderr


# in the pl code this gets called with all the devices
def _get_smart(raid_type, drive, scsi_dev):
    '''
    invokes smartctl using the appropiate controller
    '''
    scsi_dev = scsi_dev.strip()
    if raid_type == ARECA:
        fullcommand = ['smartctl', '-a', '-d', 'areca,%s' % drive, scsi_dev]
    elif raid_type == MDADM:
        fullcommand = ['smartctl', '-a', '-d', 'ata', '/dev/%s' % drive]
    elif raid_type is None:
        fullcommand = ['smartctl', '-a', '-d', 'sat', '/dev/%s' % drive]

    log.debug('_get_smart running command: %s' % str(fullcommand))
    p = Popen(fullcommand, stdout=PIPE, stderr=PIPE)
    stdout, stderr = p.communicate()
    return p.returncode, stdout, stderr


# TODO Process out the different failures here
def _filter_smart_output(smart_data):
    '''
    5 Reallocated_Sector_Ct   0x0033   100   100   036    Pre-fail  Always       -       35
    '''
    number_realloc_sectors = 0
    for line in smart_data.split('\n'):
        if line.find('Reallocated_Sector_Ct') != -1:
            log.debug('filter_smart_output processing line: %s' % str(line))
            number_realloc_sectors = line.split()[-1]

    return {'reallocated_sector_count': number_realloc_sectors}


def _check_firmware_areca():
    '''
    ubuntu@mira106:~$ sudo salt 'mira048*' cmd.run "/usr/sbin/cli64 sys info | grep -i firm "
    mira048.front.sepia.ceph.com:
        Firmware Version   : V1.49 2011-08-10
    '''
    firmware = "/usr/sbin/cli64 sys info | grep -i firm | awk '{print $5}' | cut -d '-' -f1"

    p = Popen(firmware, stdout=PIPE, stderr=PIPE, shell=True)
    stdout, stderr = p.communicate()

    if int(stdout) < 2011:
        return 1, '', 'Controller needs newer firmware for S.M.A.R.T. support'
    elif int(stdout) >= 2011:
        return 0, 'This controller is capable of SMART reporting', ''
    else:
        return 2, '', 'Failed to check firmware'


def _get_devices_areca():
    '''
    Run some Areca specific commands to determine what drives it manages
    '''
    vsf = "/usr/sbin/cli64 vsf info  | grep -v Capacity | grep -v ======== | grep -v ErrMsg | wc -l"
    p = Popen(vsf, stdout=PIPE, stderr=PIPE, shell=True)
    stdout, stderr = p.communicate()
    # TODO figure out why this is the last sg device and not the first
    scsidev = "/dev/sg%s" % stdout.strip()

    devices = "/usr/sbin/cli64 disk info | sed '/modelname/Id;/=======/d;/GuiErr/d;/Free/d;/Failed/d;'"
    d = Popen(devices, stdout=PIPE, stderr=PIPE, shell=True)
    stdout, stderr = d.communicate()
    device_list = [x.split()[0] for x in stdout.split('\n') if x]
    return scsidev, device_list


def get_errors():
    '''
    Iterate all drives we can discover and return a dictionary device: specific SMART failure states
    '''
    # areca hardware raid
    drives = 0
    report = {}
    _, pci, _ = _get_raid_devices()
    if pci.find(ARECA):
        if not _check_firmware_areca()[0]:
            sd, d = _get_devices_areca()
            for device in d:
                drives += 1
                report[','.join((sd, device))] = _filter_smart_output(_get_smart(ARECA, device, sd)[1])

    return report
