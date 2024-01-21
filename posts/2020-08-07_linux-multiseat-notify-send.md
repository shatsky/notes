---
title: How to send desktop notification to user in Linux
summary: E. g. in multiseat system to show other user a file: `sudo -u ${target_user_name} env DBUS_SESSION_BUS_ADDRESS=${target_user_dbus_session_bus_address} notify-send 'Local file URL' '<a href="file:///path/to/file">/path/to/file</a>'`
---
`DBUS_SESSION_BUS_ADDRESS` value can be checked in env of any desktop process of target user

`'Local file URL'` will be displayed as notification popup header, the rest will be rendered as content
