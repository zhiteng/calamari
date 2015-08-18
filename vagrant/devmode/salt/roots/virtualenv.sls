
virtualenv:
  virtualenv.managed:
    - user: vagrant
    - name: /home/vagrant/calamari/env
    - system_site_packages: true
    - require:
      - git: git_clone
      - pkg: build_deps

# Explicit installation for pyzmq so we can pass --zmq=bundled
pyzmq:
  pip.installed:
    - name: pyzmq == 14.1.1
    - user: vagrant
    - bin_env: /home/vagrant/calamari/env
    - activate: true
    - download_cache: /vagrant/pip_cache
    - install_options:
      - "--zmq=bundled"
    - require:
      - virtualenv: virtualenv

pip_pkgs:
  pip:
    - installed
    - user: vagrant
    - bin_env: /home/vagrant/calamari/env
    - activate: true
    - requirements: /home/vagrant/calamari/requirements/lite.txt
    - download_cache: /vagrant/pip_cache
    - env_vars: SWIG_FEATURES=-cpperraswarn
    - require:
      - virtualenv: virtualenv
      - pip: pyzmq
