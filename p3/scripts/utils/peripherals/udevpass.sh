#!/bin/bash
# name: udevpass
# description: udevpass_desc
# icon: peripherals.svg
# reboot: yes
# nocontainer

source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
source "$SCRIPT_DIR/libs/lang/${langfile}.lib"
# usb device list fetch
select_usb_device() {
    local -a usb_devices
    local -a usb_display
    local device_line
    local bus device product
    mapfile -t usb_devices < <(lsusb)
    if [[ ${#usb_devices[@]} -eq 0 ]]; then
        echo "Error: No USB devices found"
        return 1
    fi
    for device_line in "${usb_devices[@]}"; do
        bus=$(echo "$device_line" | awk '{print $2}')
        device=$(echo "$device_line" | awk '{print $4}' | sed 's/:$//')
        product=$(echo "$device_line" | cut -d' ' -f7-)
        
        usb_display+=("Bus $bus Dev $device - $product")
    done
    
    local choice
    choice=$(zenity --list \
        --title="Select USB Device" \
        --column="USB Device" \
        "${usb_display[@]}" \
        "$msg070" \
        --height=400 --width=600)

    if [[ -z "$choice" ]] || [[ $? -ne 0 ]]; then
        return 1
    fi
    if [[ "$choice" == "$msg070" ]]; then
        exit 100
    fi
    
    for i in "${!usb_display[@]}"; do
        if [[ "${usb_display[$i]}" == "$choice" ]]; then
            echo "${usb_devices[$i]}"
            return 0
        fi
    done
    return 1
}
# udev rule creator
create_udev_rules() {
    local device_line="$1"
    local vendor_id
    vendor_id=$(echo "$device_line" | sed -n 's/.*ID \([0-9a-f]*\):.*/\1/p')
    if [[ -z "$vendor_id" ]]; then
        fatal "Could not extract vendor ID from device"
    fi
    local vendor_name
    vendor_name=$(echo "$device_line" | cut -d' ' -f7 | tr '[:upper:]' '[:lower:]')
    if [[ -z "$vendor_name" ]]; then
        fatal "Could not extract vendor name from device"
    fi
    local rule_num=50
    local rule_file
    while true; do
        rule_file="/etc/udev/rules.d/${rule_num}-usb-${vendor_name}.rules"
        if [[ ! -f "$rule_file" ]]; then
            break
        fi
        rule_num=$((rule_num + 1))
    done
    
    local rule_content="KERNEL==\"hidraw*\", ATTRS{idVendor}==\"${vendor_id}\", MODE=\"0666\""
    echo "$rule_content" | sudo tee "$rule_file" > /dev/null
    if [[ $? -eq 0 ]]; then
        zeninf "$msg036"
    else
        fatal "Failed to create udev rules file"
    fi
}
# menu
main_menu() {
    while true; do
        local selected_device
        selected_device=$(select_usb_device)
        
        if [[ $? -ne 0 ]]; then
            break
        fi
        
        local bus_device
        bus_device=$(echo "$selected_device" | awk '{print $2":"$4}' | sed 's/:$//')
        zenity --info \
            --title="Selected Device" \
            --text="You selected:\n\n$selected_device\n\nBus:Device: $bus_device" \
            --height=300 --width=500
        create_udev_rules "$selected_device"
        
        break
    done
}

