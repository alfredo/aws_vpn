-- Connect to a VPN service via applescript
-- Usage:
-- Connect: osascript vpnconnection.scpt aws <URL>
-- Disconnect: osascript vpnconnection.scpt aws halted

on create_vpn_service(vpn_name)
	tell application "System Preferences"
		reveal pane "Network"
		activate
		tell application "System Events"
			tell process "System Preferences"
				tell window 1
					click button "Add Service"
					tell sheet 1
						-- set location type
						click pop up button 1
						click menu item "VPN" of menu 1 of pop up button 1
						delay 1

						-- set connection type
						click pop up button 2
						click menu item "PPTP" of menu 1 of pop up button 2
						delay 1

						-- set name of the service
						-- for some reason the standard 'set value of text field 1' would not work
						set value of attribute "AXValue" of text field 1 to vpn_name
						click button "Create"
					end tell

					click button "Apply"
				end tell
			end tell
		end tell

		quit
	end tell

	delay 2
end create_vpn_service

on update_vpn_settings(vpn_name, vpn_address, vpn_username, vpn_password)
	tell application "System Preferences"
		reveal pane "Network"
		activate

		tell application "System Events"
			tell process "System Preferences"
				tell window 1
					-- select the specified row in the service list
					repeat with r in rows of table 1 of scroll area 1
						if (value of attribute "AXValue" of static text 1 of r as string) contains vpn_name then
							select r
						end if
					end repeat

					-- set the address & username / account name
					-- note that this is vpn specific
					tell group 1
						set focused of text field 1 to true
						keystroke " "

						set value of text field 1 to vpn_address
						set value of text field 2 to vpn_username
						click button "Authentication Settings…"
					end tell

					-- open up the auth panel and set the login password
					tell sheet 1
						set focused of text field 1 to true
						set value of text field 1 to vpn_password
						click button "Ok"
					end tell

					click button "Apply"
				end tell
			end tell
		end tell

		quit
	end tell
end update_vpn_settings

on update_vpn_address(vpn_name, vpn_address)
	tell application "System Preferences"
		reveal pane "Network"
		activate

		tell application "System Events"
			tell process "System Preferences"
				tell window 1
					-- select the specified row in the service list
					repeat with r in rows of table 1 of scroll area 1
						if (value of attribute "AXValue" of static text 1 of r as string) contains vpn_name then
							select r
						end if
					end repeat

					-- set the address & username / account name
					-- note that this is vpn specific
					tell group 1
						set focused of text field 1 to true
						keystroke " "

						set value of text field 1 to vpn_address
					end tell
					click button "Apply"
				end tell
			end tell
		end tell

		quit
	end tell
end update_vpn_address

on vpn_exists(vpn_name)
	tell application "System Events"
		try
			service vpn_name of network preferences
			return true
		on error
			return false
		end try
	end tell
end vpn_exists

on vpn_status(vpn_name)
	tell application "System Events"
		return connected of configuration of service vpn_name of network preferences
	end tell
end vpn_status

on toggle_vpn_status(vpn_name)
	tell application "System Events"
		tell current location of network preferences
			set VPNservice to service vpn_name
			set isConnected to connected of current configuration of VPNservice
			if isConnected then
				disconnect VPNservice
			else
				connect VPNservice
			end if
		end tell
	end tell
end toggle_vpn_status

on run argv
	set vpn_name to (item 1 of argv)
	set vpn_address to (item 2 of argv)
	if vpn_address is not equal to "halted" then update_vpn_address(vpn_name, vpn_address)
	delay 2
	toggle_vpn_status(vpn_name)
end run