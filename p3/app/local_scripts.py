import os
import shutil
import subprocess

from .gtk_common import Gdk, Gtk, GLib
from . import parser

class LocalScriptsCtl:
    def _setup_drag_and_drop(self):
        """Setup drag-and-drop functionality but don't enable it initially."""
        self.drag_and_drop_enabled = False
        self.drag_handler_id = None
        # We'll enable/disable drag-and-drop dynamically based on the current view

    def _enable_drag_and_drop(self):
        """Enable drag-and-drop functionality for the Local Scripts category."""
        if not hasattr(self, "drag_and_drop_enabled"):
            self._setup_drag_and_drop()

        if not self.drag_and_drop_enabled:
            self.drag_dest_set(Gtk.DestDefaults.ALL, [], Gdk.DragAction.COPY)
            if self.drag_handler_id is None:
                self.drag_handler_id = self.connect(
                    "drag-data-received", self._on_drag_data_received
                )
            self.drag_dest_add_uri_targets()
            self.drag_and_drop_enabled = True

    def _disable_drag_and_drop(self):
        """Disable drag-and-drop functionality."""
        if not hasattr(self, "drag_and_drop_enabled"):
            return

        if self.drag_and_drop_enabled:
            self.drag_dest_unset()
            self.drag_and_drop_enabled = False

    def _is_local_scripts_category(self, category_info):
        """Check if the given category info represents the Local Scripts category."""
        if not category_info or not hasattr(self, "local_sh_dir"):
            return False
        return category_info.get("path") == self.local_sh_dir.rstrip("/")

    def _on_drag_data_received(self, widget, context, x, y, data, info, time):
        """Handle drag-and-drop of .sh files. Only active when viewing Local Scripts category."""
        sh_paths = [
            os.path.normpath(uri[7:])
            for uri in data.get_uris()
            if uri.startswith("file://") and uri.endswith(".sh")
        ]
        from urllib.parse import unquote

        if sh_paths:
            os.makedirs(self.local_sh_dir, exist_ok=True)
            [
                shutil.copy2(
                    unquote(sh_path),
                    f"{self.local_sh_dir}{os.path.basename(unquote(sh_path))}",
                )
                for sh_path in sh_paths
            ]

            # Refresh the current view since we know we're in Local Scripts category
            self.load_scripts(self.current_category_info)

    def on_drag_end(self, widget, drag_context):
        self.scripts_flowbox.unselect_all()

    def on_drag_data_get(self, widget, drag_context, data, info, time):
        selected_children = self.scripts_flowbox.get_selected_children()
        uris = []

        for child in selected_children:
            event_box = child.get_child()
            infos = event_box.info
            if infos.get("path"):
                uris.append(GLib.filename_to_uri(infos.get("path")))

        if not uris:
            infos = widget.info
            if infos.get("path"):
                uris.append(GLib.filename_to_uri(infos.get("path")))

        data.set_uris(uris)

    def _handle_create_new_script(self):
        """Handle the creation of a new local script."""
        # Import the InputDialog from head_menu
        from . import head_menu

        dialog = head_menu.InputDialog(parent=self)

        if dialog.run() == Gtk.ResponseType.OK:
            sh_name = dialog.get_input()
            if sh_name.strip():  # Check if name is not empty
                import re

                sh_filename = re.sub(r"[^a-z0-9-_]", "", sh_name.lower())
                if sh_filename:
                    self._create_and_open_local_sh(filename=sh_filename, name=sh_name)
                    # Refresh the current view to show the new script
                    self._refresh_current_local_scripts_view()

        dialog.destroy()

    def _create_and_open_local_sh(self, filename=None, name=None):
        """Create a new local script file and open it for editing."""
        import os

        local_sh_dir = f"{os.environ['HOME']}/.local/linuxtoys/scripts/"
        os.makedirs(local_sh_dir, exist_ok=True)

        # Get translated documentation comment
        doc_comment = self.translations.get(
            "script_template_doc_comment",
            "# Refer to the documentation at https://linuxtoys.luminhost.xyz/handbook.html for more information.",
        )

        _template_local_script = f"""#!/bin/bash
# name: {name}
# version: 1.0
# description: Local Script
# icon: local-scripts.svg

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
source "$SCRIPT_DIR/libs/helpers.lib"
_lang_
source "$SCRIPT_DIR/libs/lang/${{langfile}}.lib"

{doc_comment}
"""

        with open(f"{local_sh_dir}{filename}.sh", "w+") as f:
            f.write(_template_local_script)

        defaults = {
            "name": "No Name",
            "version": "N/A",
            "description": "",
            "icon": "application-x-executable",
            "reboot": "no",
            "repo": "",
        }

        _local_data = parser._parse_metadata_file(
            f"{local_sh_dir}{filename}.sh", defaults, self.translations
        )

        _local_data['is_script'] = True
        _local_data['is_subcategory'] = False
        self.script_cache.scripts.append(_local_data)
        self.script_cache.update_removable_for_script(_local_data)

        local_script_path = os.path.abspath(f"{local_sh_dir}{filename}.sh")
        if shutil.which("xdg-open"):
            subprocess.run(["xdg-open", local_script_path], check=False)

    def _refresh_current_local_scripts_view(self):
        """Refresh the current view if we're viewing local scripts."""
        if (
            hasattr(self, "current_category_info")
            and self.current_category_info
            and ".local/linuxtoys/scripts" in self.current_category_info.get("path", "")
        ):
            # Reload the scripts for the current local scripts view
            self._load_scripts_into_flowbox(
                self.scripts_flowbox, self.current_category_info
            )
            self.scripts_flowbox.show_all()
    
    def _is_local_script(self, script_info):
        """Check if a script is a local script that can be deleted."""
        if not script_info or not script_info.get("is_script", False):
            return False

        # Check if we're currently in the Local Scripts category
        if not self._is_local_scripts_category(self.current_category_info):
            return False

        # Check if the script path is within the local scripts directory
        script_path = script_info.get("path", "")
        if not hasattr(self, "local_sh_dir"):
            return False

        return script_path.startswith(self.local_sh_dir)

    def _delete_local_script(self, script_info):
        """Delete a local script after confirmation."""
        script_name = script_info.get("name", "Unknown Script")
        script_path = script_info.get("path", "")

        if not script_path or not os.path.exists(script_path):
            return

        # Show confirmation dialog without any icon or title
        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.OTHER,  # Use OTHER to avoid default icons
            buttons=Gtk.ButtonsType.NONE,  # Use NONE to add custom buttons
            text=self.translations.get(
                "delete_script_message",
                "Are you sure you want to delete '{script_name}'?",
            ).format(script_name=script_name),
        )

        # Add custom buttons with translations
        dialog.add_button(self.translations.get("no", "No"), Gtk.ResponseType.NO)
        dialog.add_button(self.translations.get("yes", "Yes"), Gtk.ResponseType.YES)

        # Create an empty image to hide the icon area
        empty_image = Gtk.Image()
        dialog.set_image(empty_image)

        # Add 20px padding to the top of the dialog
        message_area = dialog.get_message_area()
        message_area.set_margin_top(20)

        # Set secondary text with bold "This action cannot be undone"
        dialog.format_secondary_text(
            self.translations.get(
                "delete_script_warning", "<b>This action cannot be undone.</b>"
            )
        )

        # Enable markup for the secondary text to display bold formatting
        secondary_label = dialog.get_message_area().get_children()[
            1
        ]  # Second label is secondary text
        secondary_label.set_use_markup(True)

        response = dialog.run()
        dialog.destroy()

        if response == Gtk.ResponseType.YES:
            try:
                os.remove(script_path)
                self.script_cache.scripts[:] = filter(
                    lambda s: s.get("path") != script_path, self.script_cache.scripts
                )
                self.script_cache._removable_cache.pop(script_path, None)
                # Refresh the current view to remove the deleted script
                self._refresh_current_local_scripts_view()
            except Exception as e:
                # Show error dialog
                error_dialog = Gtk.MessageDialog(
                    transient_for=self,
                    flags=0,
                    message_type=Gtk.MessageType.ERROR,
                    buttons=Gtk.ButtonsType.OK,
                    text=self.translations.get("delete_error_title", "Delete Error"),
                )
                error_dialog.format_secondary_text(
                    self.translations.get(
                        "delete_error_message", "Failed to delete script: {error}"
                    ).format(error=str(e))
                )
                error_dialog.run()
                error_dialog.destroy()

    def _delete_local_scripts(self, script_infos):
        """Delete multiple local scripts after confirmation."""
        if not script_infos:
            return

        script_names = [info.get("name", "Unknown Script") for info in script_infos]
        names_text = ", ".join(script_names[:3])  # Show first 3 names
        if len(script_names) > 3:
            names_text += f" ... (+{len(script_names) - 3} more)"

        # Show confirmation dialog
        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.OTHER,
            buttons=Gtk.ButtonsType.NONE,
            text=self.translations.get(
                "delete_scripts_message",
                "Are you sure you want to delete {count} scripts?",
            ).format(count=len(script_infos)),
        )

        # Add custom buttons
        dialog.add_button(self.translations.get("no", "No"), Gtk.ResponseType.NO)
        dialog.add_button(self.translations.get("yes", "Yes"), Gtk.ResponseType.YES)

        # Create an empty image to hide the icon area
        empty_image = Gtk.Image()
        dialog.set_image(empty_image)

        # Add padding
        message_area = dialog.get_message_area()
        message_area.set_margin_top(20)

        # Set secondary text
        dialog.format_secondary_text(
            self.translations.get(
                "delete_script_warning",
                "<b>This action cannot be undone.</b>\n\nScripts: {names}",
            ).format(names=names_text)
        )

        # Enable markup
        secondary_label = dialog.get_message_area().get_children()[1]
        secondary_label.set_use_markup(True)

        response = dialog.run()
        dialog.destroy()

        if response == Gtk.ResponseType.YES:
            deleted_count = 0
            for script_info in script_infos:
                script_path = script_info.get("path", "")
                if script_path and os.path.exists(script_path):
                    try:
                        os.remove(script_path)
                        self.script_cache.scripts[:] = filter(
                            lambda s: s.get("path") != script_path,
                            self.script_cache.scripts,
                        )
                        self.script_cache._removable_cache.pop(script_path, None)
                        deleted_count += 1
                    except Exception as e:
                        print(f"Failed to delete {script_path}: {e}")

            # Refresh the view
            if deleted_count > 0:
                self._refresh_current_local_scripts_view()

    def _edit_local_script(self, script_info):
        """Open a local script in the user's default text editor."""
        script_path = script_info.get("path", "")

        if not script_path or not os.path.exists(script_path):
            # Show error dialog if script doesn't exist
            error_dialog = Gtk.MessageDialog(
                transient_for=self,
                flags=0,
                message_type=Gtk.MessageType.ERROR,
                buttons=Gtk.ButtonsType.OK,
                text=self.translations.get("edit_error_title", "Edit Error"),
            )
            error_dialog.format_secondary_text(
                self.translations.get(
                    "edit_error_message", "The script file could not be found."
                )
            )
            error_dialog.run()
            error_dialog.destroy()
            return

        try:
            # Use xdg-open to open the script in the default text editor
            subprocess.run(["xdg-open", os.path.abspath(script_path)], check=False)
        except Exception as e:
            # Show error dialog if opening fails
            error_dialog = Gtk.MessageDialog(
                transient_for=self,
                flags=0,
                message_type=Gtk.MessageType.ERROR,
                buttons=Gtk.ButtonsType.OK,
                text=self.translations.get("edit_error_title", "Edit Error"),
            )
            error_dialog.format_secondary_text(
                self.translations.get(
                    "edit_error_message", "Failed to open script: {error}"
                ).format(error=str(e))
            )
            error_dialog.run()
            error_dialog.destroy()

    def _export_local_script(self, script_info):
        """Export a local script to a user-chosen directory."""
        script_name = script_info.get("name", "Unknown Script")
        script_path = script_info.get("path", "")

        if not script_path or not os.path.exists(script_path):
            return

        # Create file chooser dialog
        dialog = Gtk.FileChooserDialog(
            title=self.translations.get(
                "select_export_directory", "Select Export Directory"
            ),
            parent=self,
            action=Gtk.FileChooserAction.SELECT_FOLDER,
        )

        # Add buttons
        dialog.add_button(
            self.translations.get("cancel_btn_label", "Cancel"), Gtk.ResponseType.CANCEL
        )
        dialog.add_button(
            self.translations.get("export", "Export"), Gtk.ResponseType.OK
        )

        # Set default directory to user's home
        dialog.set_current_folder(os.path.expanduser("~"))

        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            export_dir = dialog.get_filename()
            dialog.destroy()

            # Copy the script to the selected directory
            filename = os.path.basename(script_path)
            dest_path = os.path.join(export_dir, filename)

            try:
                import shutil

                shutil.copy2(script_path, dest_path)

            except Exception as e:
                # Show error dialog
                error_dialog = Gtk.MessageDialog(
                    transient_for=self,
                    flags=0,
                    message_type=Gtk.MessageType.ERROR,
                    buttons=Gtk.ButtonsType.OK,
                    text=self.translations.get("export_error_title", "Export Error"),
                )
                error_dialog.format_secondary_text(
                    self.translations.get(
                        "export_error_message", "Failed to export script: {error}"
                    ).format(error=str(e))
                )
                error_dialog.run()
                error_dialog.destroy()
        else:
            dialog.destroy()

    def _export_local_scripts(self, script_infos):
        """Export multiple local scripts to a user-chosen directory."""
        if not script_infos:
            return

        # Create file chooser dialog
        dialog = Gtk.FileChooserDialog(
            title=self.translations.get(
                "select_export_directory", "Select Export Directory"
            ),
            parent=self,
            action=Gtk.FileChooserAction.SELECT_FOLDER,
        )

        # Add buttons
        dialog.add_button(
            self.translations.get("cancel_btn_label", "Cancel"), Gtk.ResponseType.CANCEL
        )
        dialog.add_button(
            self.translations.get("export", "Export"), Gtk.ResponseType.OK
        )

        # Set default directory to user's home
        dialog.set_current_folder(os.path.expanduser("~"))

        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            export_dir = dialog.get_filename()
            dialog.destroy()

            # Copy all scripts to the selected directory
            success_count = 0
            for script_info in script_infos:
                script_path = script_info.get("path", "")
                if script_path and os.path.exists(script_path):
                    filename = os.path.basename(script_path)
                    dest_path = os.path.join(export_dir, filename)
                    try:
                        shutil.copy2(script_path, dest_path)
                        success_count += 1
                    except Exception as e:
                        print(f"Failed to export {filename}: {e}")

            # Show success message
            if success_count > 0:
                success_dialog = Gtk.MessageDialog(
                    transient_for=self,
                    flags=0,
                    message_type=Gtk.MessageType.INFO,
                    buttons=Gtk.ButtonsType.OK,
                    text=self.translations.get("export_success", "Export Successful"),
                )
                # Create an empty image to hide the icon area
                empty_image = Gtk.Image()
                success_dialog.set_image(empty_image)
                success_dialog.format_secondary_text(
                    self.translations.get(
                        "export_success_message",
                        "{count} scripts exported successfully.",
                    ).format(count=success_count)
                )
                message_area = success_dialog.get_message_area()
                message_area.set_margin_top(20)
                success_dialog.run()
                success_dialog.destroy()

        else:
            dialog.destroy()

    def _configure_local_scripts_interaction(self, flowbox, category_info):
        is_local = self._is_local_scripts_category(category_info)

        if is_local:
            flowbox.set_selection_mode(Gtk.SelectionMode.MULTIPLE)
            self._enable_drag_and_drop()
        else:
            flowbox.unselect_all()
            flowbox.set_selection_mode(Gtk.SelectionMode.NONE)
            self._disable_drag_and_drop()
