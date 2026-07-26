[![CI](https://github.com/guidugli/ansible-role-sudo/actions/workflows/CI.yml/badge.svg)](https://github.com/guidugli/ansible-role-sudo/actions/workflows/CI.yml)
[![Release](https://img.shields.io/github/v/tag/guidugli/ansible-role-sudo?sort=semver)](https://github.com/guidugli/ansible-role-sudo/tags)
[![Galaxy](https://img.shields.io/badge/galaxy-guidugli.sudo-blue.svg)](https://galaxy.ansible.com/ui/standalone/roles/guidugli/sudo/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

# Ansible Role: sudo

Install and configure `sudo` with CIS-aligned sudoers defaults, command logging, validation, and Molecule-based testing across supported Linux distributions. The role focuses on secure defaults, idempotent execution, and sudoers validation through `visudo`.

## Requirements

- Ansible Core 2.14 or newer
- Python available on managed hosts
- `sudo` package available from the target operating system repositories
- External privilege escalation (`become: true`) when managing:
  - `/etc/sudoers`
  - `/etc/sudoers.d/*`
  - `/var/log/sudo.log`
  - system packages

Supported Molecule platforms:
- Ubuntu 26.04
- Ubuntu 24.04
- Debian 13
- Debian 12
- Fedora 44
- Fedora 43

## Variables

| Variable | Type | Default | Description |
|-----------|--------|-----------|-------------|
| `sudo_config_file_name` | string | `01_ansible` | Name of the managed sudoers drop-in file under `/etc/sudoers.d`. |
| `sudo_admin_group` | string | `admin` | Group granted sudo access. |
| `sudo_admin_password_required` | boolean | `true` | Require authentication for sudo access. |
| `sudo_log` | string | `/var/log/sudo.log` | Sudo command log location. Set to an empty string to disable logfile management. |
| `sudo_default_parameters` | list[string] | see below | Sudoers `Defaults` directives rendered into `/etc/sudoers`. |

Default `sudo_default_parameters`:

```yaml
sudo_config_file_name: 01_ansible
sudo_admin_group: admin
sudo_admin_password_required: true
sudo_log: /var/log/sudo.log
 
sudo_default_parameters:
  - "!visiblepw"
  - always_set_home
  - match_group_by_gid
  - env_reset
  - env_keep = "COLORS DISPLAY HOSTNAME HISTSIZE KDEDIR LS_COLORS"
  - env_keep += "MAIL QTDIR USERNAME LANG LC_ADDRESS LC_CTYPE"
  - env_keep += "LC_COLLATE LC_IDENTIFICATION LC_MEASUREMENT LC_MESSAGES"
  - env_keep += "LC_MONETARY LC_NAME LC_NUMERIC LC_PAPER LC_TELEPHONE"
  - env_keep += "LC_TIME LC_ALL LANGUAGE LINGUAS _XKB_CHARSET XAUTHORITY"
  - secure_path="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/snap/bin"
  - use_pty
  - timestamp_timeout=5
  - passwd_timeout=1
  - umask=0077
```

### Internal Variables
 
These variables are maintained in `vars/main.yml` and are not intended to be overridden.
 
```yaml
sudo_path_regex: '^/'
 
sudo_default_groups_map:
  default:
    - wheel
  Debian:
    - admin
    - sudo
  Ubuntu:
    - admin
    - sudo
  RedHat:
    - wheel
  Fedora:
    - wheel
```

## Example Playbook

```yaml
---
- name: Configure sudo securely
  hosts: all
  become: true
  roles:
    - role: guidugli.sudo
      vars:
        sudo_config_file_name: 01_ansible
        sudo_admin_group: sudo
        sudo_admin_password_required: true
        sudo_log: /var/log/sudo.log
```

Passwordless sudo example:

```yaml
---
- name: Configure passwordless sudo for wheel
  hosts: all
  become: true
  roles:
    - role: guidugli.sudo
      vars:
        sudo_admin_group: wheel
        sudo_admin_password_required: false
```

### Disable Sudo Logging
 
```yaml
---
- name: Configure sudo without logfile management
  hosts: all
  become: true
 
  roles:
    - role: guidugli.sudo
      vars:
        sudo_log: ""
```

## Molecule Testing

This role uses Molecule with Podman and shared converge/verify logic:

- `molecule/shared/converge.yml`
- `molecule/shared/verify.yml`
- `molecule/default/`
- `molecule/systemd/`

Run tests:

```bash
molecule test -s default
molecule test -s systemd
```

The verify play validates:
- `sudo` binary exists
- `visudo` binary exists
- `/etc/sudoers` passes validation
- `Defaults use_pty` is present
- `Defaults !use_pty` is absent
- Managed sudoers drop-in exists
- Managed sudoers drop-in passes `visudo` validation

## Execution notes

### Privilege model

The role does not enforce privilege escalation internally. Tasks that install packages or manage `/etc/sudoers`, `/etc/sudoers.d`, and `/var/log/sudo.log` require sufficient external privilege. In production playbooks, set `become: true` at the play or role-call level when needed.

### Sudoers Validation
 
All role-managed sudoers content is validated before deployment using:
 
```bash
visudo -cf
```
 
Invalid sudoers content will not be written to the target host. 

### Container and systemd behavior

The role does not manage services and does not call `systemctl`, `service`, `mount`, or `sysctl`. It is suitable for non-systemd containers. The systemd Molecule scenario is retained for template alignment and future compatibility coverage, but no systemd-specific behavior is required for the current role.

## License
 
MIT
 
## Author
 
Carlos Guidugli
