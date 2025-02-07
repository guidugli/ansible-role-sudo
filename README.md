Ansible Role: sudo
=========

An Ansible Role that install and do basic configuration of sudo on RHEL/CentOS, Fedora and Debian/Ubuntu.

Requirements
------------

No additional requirements.

Role Variables
--------------

    sudo_config_file_name: 01_ansible

Any setting will be written in files on sudoers.d directory. Choose a name to hold the settings in the scope of this role.

    sudo_admin_group: admin

Specify admin group that can run any command as root

    sudo_admin_password_required: true

Specify is the admin group is required to enter a password or not when running sudo

    sudo_log: /var/log/sudo.log

If defined, add sudo configuration to generate log at the defined location.

    sudo_default_parameters:
      - "!visiblepw"
      - always_set_home
      - match_group_by_gid
      - env_reset
      - env_keep =  "COLORS DISPLAY HOSTNAME HISTSIZE KDEDIR LS_COLORS"
      - env_keep += "MAIL QTDIR USERNAME LANG LC_ADDRESS LC_CTYPE"
      - env_keep += "LC_COLLATE LC_IDENTIFICATION LC_MEASUREMENT LC_MESSAGES"
      - env_keep += "LC_MONETARY LC_NAME LC_NUMERIC LC_PAPER LC_TELEPHONE"
      - env_keep += "LC_TIME LC_ALL LANGUAGE LINGUAS _XKB_CHARSET XAUTHORITY"
      - secure_path="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/snap/bin"
      - use_pty

Set the default parameters for sudo. Read sudoers man page for more information. Also check security guides for reference on secure settings.


Dependencies
------------

No dependencies.

Example Playbook
----------------

Including an example of how to use your role (for instance, with variables passed in as parameters) is always nice for users too:

    - hosts: servers
      roles:
         - { role: guidugli.sudo }

License
-------

MIT / BSD

Author Information
------------------

This role was created in 2020 by Carlos Guidugli.
