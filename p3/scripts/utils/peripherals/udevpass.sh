#!/bin/bash
# name: udevpass
# description: udevpass_desc
# icon: peripherals.svg
# reboot: yes
# nocontainer
# new

source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_

# USB device list fetch
select_usb_device() {
    local -a rows
    local line vendor_id product_id vendor_name product
    while IFS= read -r line; do
        vendor_id=$(awk '{print $6}' <<<"$line" | cut -d: -f1)
        product_id=$(awk '{print $6}' <<<"$line" | cut -d: -f2)
        vendor_name=$(awk '{print $7}' <<<"$line")
        product=$(cut -d' ' -f7- <<<"$line")
        rows+=("$vendor_id" "$product_id" "$vendor_name" "$product")
    done < <(lsusb)

    [[ ${#rows[@]} -eq 0 ]] && return 1

    zenity --list \
        --title="Select USB Device" \
        --column="Vendor ID" \
        --column="Product ID" \
        --column="Vendor" \
        --column="Device" \
        --hide-column=1 \
        --hide-column=2 \
        --hide-column=3 \
        --print-column=ALL \
        "${rows[@]}" \
        --height=400 \
        --width=600
}

# udev rule creator
create_udev_rules() {
    local vendor_id="$1"
    local product_id="$2"
    local vendor_name="$3"
    vendor_name=${vendor_name,,}
    vendor_name=${vendor_name//[^[:alnum:]_-]/_}
    local rule_file
    if is_solus; then
        rule_file="/usr/lib/udev/rules.d/50-usb-${vendor_name}-${vendor_id}-${product_id}.rules"
    else
        rule_file="/etc/udev/rules.d/50-usb-${vendor_name}-${vendor_id}-${product_id}.rules"
    fi

    local rule_content="SUBSYSTEM==\"hidraw\", ATTRS{idVendor}==\"${vendor_id}\", ATTRS{idProduct}==\"${product_id}\", MODE=\"0666\""
    if echo "$rule_content" | sudo tee "$rule_file" >/dev/null; then
        _append_transmap "created $rule_file"
        zeninf "$msg036"
    else
        fatal "Failed to create udev rules file"
    fi
}

# Menu
main_menu() {
    local selection
    local vendor_id
    local product_id
    local vendor_name
    local device_name

    if ! selection=$(select_usb_device); then
        return
    fi

    IFS='|' read -r vendor_id product_id vendor_name device_name <<<"$selection"

    zeninf "You selected:\n\n$device_name\n\nVendor ID: $vendor_id\nProduct ID: $product_id"

    sudo_rq
    create_udev_rules "$vendor_id" "$product_id" "$vendor_name"
    if ! getent group plugdev >/dev/null; then
        sudo groupadd plugdev || fatal "Failed to create plugdev group"
    fi
    sudo usermod -aG plugdev,input "$USER"
    sudo udevadm control --reload-rules
    sudo udevadm trigger
}
main_menu

