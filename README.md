# Ansible Role: `sudo`

Install and configure `sudo` across multiple Linux distributions with a focus on **secure defaults** and **CIS-aligned configuration**.

This role supports:
- Ubuntu (24.04, 26.04)
- Debian (12, 13)
- Fedora (43, 44)

It is designed to be:
- multi-distro compatible
- container-friendly (tested via Molecule + Podman)
- aligned with security recommendations (for example, sudo logging)

---

## Features

- Installs and configures `sudo`
- Manages sudoers configuration via `/etc/sudoers.d/`
- Applies configurable `Defaults` parameters
- Optionally enforces sudo command logging
- Validates all generated sudoers files using `visudo`
- Enforces classic sudo behavior on Ubuntu 26.04+ when needed for compatibility with CIS-style logging requirements

---

## Important: Ubuntu 26.04+ and `sudo-rs`

Ubuntu 26.04 ships `sudo-rs` (Rust-based sudo) by default.

This role is intended to support secure standards and CIS-aligned configuration. In particular, CIS-style guidance commonly expects a sudoers logfile directive such as:

```text
Defaults logfile="/var/log/sudo.log"
```

Because `sudo-rs` does not fully support the same sudoers feature set as classic sudo, this role is designed around **classic sudoers compatibility** for policy validation and configuration management.

---

## Requirements

- Ansible >= 2.14
- Python available on target hosts
- Root or privilege escalation capability to manage system packages and `/etc/sudoers*`

---

## Role Variables

### Default Variables (`defaults/main.yml`)

| Variable | Default | Description |
|----------|---------|-------------|
| `sudo_config_file_name` | `01_ansible` | Name of the sudoers drop-in file created under `/etc/sudoers.d/` |
| `sudo_admin_group` | `admin` | Group granted broad sudo access |
| `sudo_admin_password_required` | `true` | Whether members of the admin group must authenticate with a password |
| `sudo_log` | `/var/log/sudo.log` | Path used for sudo command logging |
| `sudo_default_parameters` | see below | List of `Defaults` directives rendered into `/etc/sudoers` |

### Default sudo parameters

```yaml
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
```

### Internal Variables (`vars/main.yml`)

These variables are used internally by the role.

| Variable | Default | Description |
|----------|---------|-------------|
| `pathre` | `^(?:[/\])` | Regular expression used to validate filesystem paths |
| `_sudo_default_groups` | distro map | Reference mapping of common admin groups by distribution |
| `sudo_default_groups` | derived | Derived fallback list of default sudo-capable groups |

#### Internal group mapping reference

```yaml
_sudo_default_groups:
  default: ['wheel']
  Debian: ['admin', 'sudo']
  Ubuntu: ['admin', 'sudo']
```

> Note: the current role logic primarily relies on `sudo_admin_group` supplied through defaults or overrides. The `sudo_default_groups` mapping exists as internal reference/fallback logic in `vars/main.yml`.

---

## Validation

The role validates inputs in two layers:

1. **`meta/argument_specs.yml`**
   - validates required variables and basic types
2. **`tasks/asserts.yml`**
   - validates regex/content constraints such as:
     - `sudo_config_file_name`
     - `sudo_admin_group`
     - `sudo_log`
     - `sudo_default_parameters`

All rendered sudoers files are also validated with:

```bash
visudo -cf <file>
```

This helps prevent invalid sudoers content from being deployed.

---

## Example Playbook

```yaml
- name: Configure sudo securely
  hosts: all
  become: true

  roles:
    - role: guidugli.sudo
      vars:
        sudo_config_file_name: 01_ansible
        sudo_admin_group: admin
        sudo_admin_password_required: true
        sudo_log: /var/log/sudo.log
```

### Example with passwordless admin group

```yaml
- name: Configure passwordless sudo for an admin group
  hosts: all
  become: true

  roles:
    - role: guidugli.sudo
      vars:
        sudo_admin_group: wheel
        sudo_admin_password_required: false
```

---

## What the role configures

### 1. Admin group rule in `/etc/sudoers.d/<file>`

Example result:

```text
%admin ALL=(ALL:ALL) ALL
```

or, when passwordless sudo is enabled:

```text
%admin ALL=(ALL:ALL) NOPASSWD: ALL
```

### 2. Main `/etc/sudoers` file from template

The role deploys the main sudoers file from `templates/sudoers.j2` and includes:

- the configured `Defaults` parameters
- the `root` rule
- `#includedir /etc/sudoers.d`

### 3. Optional logfile setting

When `sudo_log` is defined, the role adds a sudoers logging setting under the managed drop-in file.

---

## Testing

This role uses **Molecule + Podman**.

### Supported scenarios

- `default`
- `systemd`

Shared converge/verify logic is stored in `molecule/shared/`, while scenario-specific bootstrap and container lifecycle logic remains in the respective scenario directories.

### Run tests locally

```bash
./scripts/run_local.sh
```

Or run scenarios individually:

```bash
molecule test -s default
molecule test -s systemd
```

---

## Release metadata workflow

This repository uses generated metadata based on the shared Molecule OS matrix.

### Source of truth

```text
molecule/shared/vars.yml
```

This drives:
- tested platform matrix
- generated scenario inventories
- generated `meta/main.yml`

### Refresh metadata

```bash
./scripts/update_release_metadata.sh
```

### Release helper

```bash
./scripts/release.sh --version v1.1.0 --message "Release v1.1.0"
```

---

## Relevant project structure

```text
defaults/
  main.yml

vars/
  main.yml

tasks/
  main.yml
  asserts.yml
  sudo.yml

templates/
  sudoers.j2
  meta_main.yml.j2

meta/
  argument_specs.yml
  main.yml

molecule/
  shared/
  default/
  systemd/
```

---

## Design principles

- Secure-by-default configuration
- Validation before deployment
- CIS-oriented sudo policy support
- Multi-distro compatibility
- Reproducible Molecule-based test coverage
- Generated Galaxy metadata from the tested OS matrix

---

## License

MIT

---

## Author

Carlos Guidugli
