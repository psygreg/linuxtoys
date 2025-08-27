from .gtk_common import Gtk


class ContextMenu(Gtk.Menu):
    def __init__(self, script_runner):
        super().__init__()
        self.script_runner = script_runner

        remove_item = Gtk.MenuItem(label="Uninstall")
        remove_item.connect("activate", self.__on_context_remove)
        
        self.append(remove_item)
        self.show_all()

    def __on_context_remove(self, widget):
        """Handle remove / uninstall"""
        self.info['arg'] = 'remove'

        self.script_is_running = True

        def completion_handler():
            self.script_is_running = False
            self.info.pop('arg', None)
                
        def reboot_handler():
            self.reboot_required = True
              
        self.script_runner.run_script(
            self.info, 
            on_completion=completion_handler,
            on_reboot_required=reboot_handler
        )