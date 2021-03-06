# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTIBILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.


import bpy
from . import sheepit


def register():
    bpy.utils.register_class(LoginPanel)
    bpy.utils.register_class(AddProjectPanel)
    bpy.utils.register_class(ProfilePanel)


def unregister():
    bpy.utils.unregister_class(LoginPanel)
    bpy.utils.unregister_class(AddProjectPanel)
    bpy.utils.unregister_class(ProfilePanel)


class SheepItRenderPanel():
    """ SheepIt panel in the Render tab """
    bl_label = "SheepIt!"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "render"


class LoginPanel(SheepItRenderPanel, bpy.types.Panel):
    """ Login Panel, will be hidden if allready logged in """
    bl_idname = "SHEEPIT_PT_login_panel"
    bl_options = {'DEFAULT_CLOSED'}
    @classmethod
    def poll(cls, context):
        preferences = context.preferences.addons[__package__].preferences
        return not preferences.logged_in

    def draw(self, context):
        self.layout.operator("sheepit.login")
        self.layout.operator("sheepit.create_account")


class AddProjectPanel(SheepItRenderPanel, bpy.types.Panel):
    """ Add Project Menu in the render Panel,
        this will be disabled if not logged in """
    bl_idname = "SHEEPIT_PT_add_project"
    bl_options = {'DEFAULT_CLOSED'}
    @classmethod
    def poll(cls, context):
        preferences = context.preferences.addons[__package__].preferences
        return preferences.logged_in

    def draw(self, context):
        supported_renderers = {'CYCLES', 'BLENDER_EEVEE'}
        if bpy.context.scene.render.engine in supported_renderers:
            # Renderable by all members
            self.layout.prop(context.scene.sheepit_properties, "public")

            # Select device
            compute_method = self.layout.row(align=True)
            if bpy.context.scene.render.engine == 'CYCLES':
                # for Cycles
                compute_method.prop(
                    context.scene.sheepit_properties, "cpu", toggle=True)
                compute_method.prop(
                    context.scene.sheepit_properties, "cuda", toggle=True)
                compute_method.prop(context.scene.sheepit_properties,
                                    "opencl", toggle=True)
            else:
                # for Eevee
                compute_method.prop(
                    context.scene.sheepit_properties, "nvidia", toggle=True)
                compute_method.prop(context.scene.sheepit_properties,
                                    "amd", toggle=True)

            # Select job type (Animation or still)
            self.layout.prop(context.scene.sheepit_properties,
                             "type", expand=True)

            settings = self.layout.column(align=True)
            if context.scene.sheepit_properties.type == 'frame':
                # settings for Single Frame renders
                settings.prop(context.scene, "frame_current")
            else:
                # settings for Animations
                settings.prop(context.scene, "frame_start")
                settings.prop(context.scene, "frame_end")
                settings.prop(context.scene, "frame_step")
                settings.prop(context.scene.sheepit_properties, "mp4")
            # frame splitting
            split_layers = False
            if bpy.context.scene.render.engine == 'CYCLES' \
                    and bpy.context.scene.use_nodes:
                split_layers = True

            if context.scene.sheepit_properties.type == 'frame':
                if split_layers:
                    self.layout.prop(context.scene.sheepit_properties,
                                     "still_layer_split")
                else:
                    self.layout.label(
                        text="The frame will be split in 8x8 tiles.")
            else:
                if split_layers:
                    self.layout.prop(context.scene.sheepit_properties,
                                     "anim_layer_split")
                else:
                    split_frame = self.layout.row(align=True)
                    split_frame.prop(context.scene.sheepit_properties,
                                     "anim_split", expand=True)
                    if context.scene.sheepit_properties.anim_split != '1':
                        self.layout.label(
                            text="If you split frames, compositor and "
                            "denoising will be disabled.")

            self.layout.operator("sheepit.send_project")
            status = ""
            progress = ""
            # status
            if 'sheepit' in bpy.context.window_manager and \
                    'upload_status' in bpy.context.window_manager['sheepit']:
                status = bpy.context.window_manager['sheepit']['upload_status']
            # progress
            if 'sheepit' in bpy.context.window_manager and \
                    'progress' in bpy.context.window_manager['sheepit']:
                progress = bpy.context.window_manager['sheepit']['progress']
                progress = f"{progress}%"
            if progress and status:
                self.layout.label(text=f"{status}... {progress}")
            elif status:
                self.layout.label(text=status)
            device_valid = False
            if bpy.context.scene.render.engine == 'CYCLES':
                device_valid = (context.scene.sheepit_properties.cpu or
                                context.scene.sheepit_properties.cuda or
                                context.scene.sheepit_properties.opencl)

            else:
                device_valid = (context.scene.sheepit_properties.amd or
                                context.scene.sheepit_properties.nvidia)
            if not device_valid:
                self.layout.label(
                    text="You need to set a compute method "
                    "before adding a project.")
        else:
            self.layout.label(
                text="SheepIt is only compatible with Eevee or Cycles")


class ProfilePanel(SheepItRenderPanel, bpy.types.Panel):
    """ Profile Panel shown under the Submit Panel
        Used for Userinfo, logout and other Profile operations """
    bl_idname = "SHEEPIT_PT_profile_panel"
    bl_parent_id = "SHEEPIT_PT_add_project"
    bl_label = "Profile"
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        preferences = context.preferences.addons[__package__].preferences
        return preferences.logged_in

    def draw(self, context):
        preferences = context.preferences.addons[__package__].preferences

        self.layout.label(text=f"logged in as {preferences.username}")

        # profile information
        if 'sheepit' in bpy.context.window_manager and \
                'profile' in bpy.context.window_manager['sheepit']:
            profile = bpy.context.window_manager['sheepit']['profile']
            try:
                self.layout.label(text=f"Points: {profile['Points']}")
                self.layout.label(text=f"Rank: {profile['Rank']}")
            except KeyError:
                pass

        self.layout.operator("sheepit.refresh_profile")
        self.layout.operator("sheepit.logout")
