Ansible Role: sudo
=========

An Ansible Role that install and configure sudo on RHEL/CentOS, Fedora and Debian/Ubuntu.

Requirements
------------

No additional requirements.

Role Variables
--------------

    sudo_config_file_name: 01_ansible

Any setting will be written in files on sudoers.d directory. Choose a name to hold the settings in the scope of this role.

    sudo_admin_group: admin

If specified, the default groups like wheel, admin, sudo will be disabled, and the specified group enabled, so users of the specified group are able to sudo to any command.

    sudo_log: /var/log/sudo.log

If defined, add sudo configuration to generate log at the defined location.

    sudo_cmd_use_pty: yes

A few times, attackers can run a malicious program (such as a virus or malware) using sudo, which would again fork a background process that remains on the user’s terminal device even when the main program has finished executing. To avoid such a scenario, you can configure sudo to run other commands only from a psuedo-pty using the use_pty parameter, whether I/O logging is turned on or not, set variable below to yes. Setting this variable to no will only cause the role to remove use_pty entry from the custom sudo file.

    #sudo_secure_path: '/sbin:/bin:/usr/sbin:/usr/bin'

This is the path used for every command run with sudo, it has two importances:
- Used when a system administrator does not trust sudo users to have a secure PATH environment variable
- To separate “root path” and “user path”, only users defined by exempt_group are not affected by this setting.



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
