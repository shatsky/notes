---
title: fwknop on NixOS for single packet authentication
summary: Hide your private NixOS server from hordes of crackers which scan IPs and probe for vulnerabilities, while retaining ability to access it yourself from any network
---
How this works:
- firewall is initially configured to drop all incoming packets
- fwknopd captures packets on specified interface and upon capturing UDP packet with dest port 62201 it checks its contents as fwknop auth packet; note that by default fwknopd doesn't bind to this port, with all ports closed by firewall it's not possible to receive packet with dest port via binding/listening to it as regular network service daemons do, so fwknopd works like sniffer (though it's also possible to run it in UDP server/listener mode)
- if captured packet is valid fwknop auth packet aka "knock", successfully decrypted with specified pre shared aes key, and its hmac is successfully validated with preshared hmac key, and it contains nonce which is valid for current time interval and not present in fwknopd ring buffer for nonces already received within current time interval (to prevent replay attacks), fwknopd adds temporary firewall exception rule which opens specified port for single IP address specified in knock packet (connections which are established while the port is opened will survive expiration of this rule, as firewall is normally configured to accept incoming packets which belong to already established connections)

*Obviously gateways which carry traffic between your client and your server can see that your server exists and is protected like this, possibly drawing attention to it from even more powerful entities, but that's a matter of choice:)*

*fwknop is for FireWall Knock OPerator*

fwknop package including both fwknopd server and fwknop client is in nixpkgs, but it's regular package which is installed into its Nix store path and isn't "integrated" into NixOS in any way. To make it run as systemd service with my config, I explicitly declare systemd service and config files in /etc in my configuration.nix:

```
  systemd.services.fwknopd = {
    description = "fwknopd Service";
    after = [ "network.target" ];
    serviceConfig.ExecStart = "${pkgs.fwknop}/bin/fwknopd --conf /etc/fwknop/fwknopd.conf --foreground";
    wantedBy = [ "multi-user.target" ];
  };
  environment.etc."fwknop/fwknopd.conf".text = ''
    PCAP_INTF           eth0;
  '';
  environment.etc."fwknop/access.conf".text = ''
    SOURCE                     ANY
    OPEN_PORTS                 tcp/22
    REQUIRE_SOURCE_ADDRESS     Y
    KEY_BASE64:                Sz80RjpXOlhH2olGuKBUamHKcqyMBsS9BTgLaMugUsg=
    HMAC_KEY_BASE64:           c0TOaMJ2aVPdYTh4Aa25Dwxni7PrLo2zLAtBoVwSepkvH6nLcW45Cjb9zaEC2SQd03kaaV+Ckx3FhCh5ohNM5Q==
  '';
```

These keys are from documentation example, don't bother trying to find my server:) Convenient fwknop client cmd to generate random keys: `fwknop --key-gen`

fwknop client command to send auth packet: `fwknop --access tcp/22 --allow-ip ${CLIENT_IP} --destination ${SERVER_IP} --key-base64-rijndael ${KEY_BASE64} --key-base64-hmac ${HMAC_KEY_BASE64}` (or check docs to make it read keys from file so that they are not visible in process cmdline)

NixOS by default allows incoming ICMPv4 echo requests, to prevent this: `networking.firewall.allowPing = false`

NixOS by default opens ports for network services which you enable via its config, to prevent this for sshd: `services.openssh.openFirewall = false`

And just to have all in one place, to allow SSH access for just one user and only with key auth:

```
services.openssh.settings = {
  PasswordAuthentication = false;
  KbdInteractiveAuthentication = false;
  AllowUsers = [ "user" ];
};
```

and add public key to ~user/.ssh/authorized_keys
