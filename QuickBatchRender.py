# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

"""
1.0
    Split off to separate addon.
"""


import bpy
import os


bl_info = {
    "name": "Quick Batch Render",
    "description": "Render sequences in the timeline to individual files and automatically create a new copy of the current scene with these strips replaced with the rendered versions.",
    "author": "Hudson Barkley (Snu/snuq/Aritodo)",
    "version": (1, 0, 0),
    "blender": (2, 79, 0),
    "location": "Sequencer Panel",
    "wiki_url": "https://github.com/snuq/QuickBatchRender",
    "tracker_url": "https://github.com/snuq/QuickBatchRender/issues",
    "category": "Sequencer"
}


def copy_curves(copy_from, copy_to, scene_from, scene_to):
    """Copies animation curves from one sequence to another, this is needed since the copy operator doesn't do this...
    Arguments:
        copy_from: VSE Sequence object to copy from
        copy_to: VSE Sequence object to copy to
        scene_from: scene that copy_from is in
        scene_to: scene that copy_to is in"""
    if hasattr(scene_from.animation_data, 'action'):
        scene_to.animation_data_create()
        scene_to.animation_data.action = bpy.data.actions.new(name=scene_to.name+'Action')
        for fcurve in scene_from.animation_data.action.fcurves:
            path = fcurve.data_path
            path_start = path.split('[', 1)[0]
            path_end = path.split(']')[-1]
            test_path = path_start+'["'+copy_from.name+'"]'+path_end
            if path == test_path:
                new_path = path_start+'["'+copy_to.name+'"]'+path_end
                new_curve = scene_to.animation_data.action.fcurves.new(data_path=new_path)
                new_curve.extrapolation = fcurve.extrapolation
                new_curve.mute = fcurve.mute
                #copy keyframe points to new_curve
                for keyframe in fcurve.keyframe_points:
                    new_curve.keyframe_points.add()
                    new_keyframe = new_curve.keyframe_points[-1]
                    new_keyframe.type = keyframe.type
                    new_keyframe.amplitude = keyframe.amplitude
                    new_keyframe.back = keyframe.back
                    new_keyframe.co = keyframe.co
                    new_keyframe.easing = keyframe.easing
                    new_keyframe.handle_left = keyframe.handle_left
                    new_keyframe.handle_left_type = keyframe.handle_left_type
                    new_keyframe.handle_right = keyframe.handle_right
                    new_keyframe.handle_right_type = keyframe.handle_right_type
                    new_keyframe.interpolation = keyframe.interpolation
                    new_keyframe.period = keyframe.period
                new_curve.update()


def batch_render_complete_handler(scene):
    """Handler called when each element of a batch render is completed"""

    scene.quick_batch.batch_rendering = False
    handlers = bpy.app.handlers.render_complete
    for handler in handlers:
        if "batch_render_complete_handler" in str(handler):
            handlers.remove(handler)


def batch_render_cancel_handler(scene):
    """Handler called when the user cancels a render that is part of a batch render"""

    scene.quick_batch.batch_rendering_cancel = True
    handlers = bpy.app.handlers.render_cancel
    for handler in handlers:
        if "batch_render_cancel_handler" in str(handler):
            handlers.remove(handler)


class QuickBatchRenderPanel(bpy.types.Panel):
    """Panel for displaying QuickBatchRender settings and operators"""

    bl_label = "Quick Batch Render"
    bl_space_type = 'SEQUENCE_EDITOR'
    bl_region_type = 'UI'
    bl_category = "Batch Render"

    @classmethod
    def poll(cls, context):
        del context
        #Check for sequences
        if not bpy.context.sequences:
            return False
        if len(bpy.context.sequences) > 0:
            return True
        else:
            return False

    def draw(self, context):
        scene = context.scene
        quick_batch = scene.quick_batch

        layout = self.layout
        row = layout.row()
        row.operator('qbr.quickbatchrender', text='Batch Render')
        row = layout.row()
        row.prop(quick_batch, 'batch_render_directory')
        row = layout.row()
        row.prop(quick_batch, 'batch_selected', toggle=True)
        row = layout.row()
        row.prop(quick_batch, 'batch_effects', toggle=True)
        row.prop(quick_batch, 'batch_audio', toggle=True)
        row = layout.row()
        row.prop(quick_batch, 'batch_meta')
        box = layout.box()
        row = box.row()
        row.label("Render Presets:")
        row = box.row()
        row.prop(quick_batch, 'video_settings_menu', text='Opaque Strips')
        row = box.row()
        row.prop(quick_batch, 'transparent_settings_menu', text='Transparent Strips')
        row = box.row()
        row.prop(quick_batch, 'audio_settings_menu', text='Audio Strips')


class QuickBatchRender(bpy.types.Operator):
    """Modal operator that runs a batch render on all sequences in the timeline"""

    bl_idname = 'qbr.quickbatchrender'
    bl_label = 'VSEQF Quick Batch Render'
    bl_description = 'Renders out sequences in the timeline to a folder and reimports them.'

    _timer = None

    rendering = bpy.props.BoolProperty(default=False)
    renders = []
    rendering_sequence = None
    rendering_scene = None
    original_scene = None
    file = bpy.props.StringProperty('')
    total_renders = bpy.props.IntProperty(0)
    total_frames = bpy.props.IntProperty(0)
    audio_frames = bpy.props.IntProperty(0)
    rendering_scene_name = ''

    def set_render_settings(self, scene, setting, transparent):
        """Applies a render setting preset to a given scene

        Arguments:
            scene: Scene object to apply the settings to
            setting: String, the setting preset name to apply.  Accepts values in the quick_batch setting 'video_settings_menu'
            transparent: Boolean, whether this scene should be set up to render transparency or not"""

        pixels = scene.render.resolution_x * scene.render.resolution_y * (scene.render.resolution_percentage / 100)
        if setting == 'DEFAULT':
            if transparent:
                scene.render.image_settings.color_mode = 'RGBA'
            else:
                scene.render.image_settings.color_mode = 'RGB'
        elif setting == 'AVIJPEG':
            scene.render.image_settings.file_format = 'AVI_JPEG'
            scene.render.image_settings.color_mode = 'RGB'
            scene.render.image_settings.quality = 95
        elif setting == 'H264':
            #Blender 2.79 will change this setting, so this is to ensure backwards compatibility
            try:
                scene.render.image_settings.file_format = 'H264'
            except:
                scene.render.image_settings.file_format = 'FFMPEG'
            scene.render.image_settings.color_mode = 'RGB'
            scene.render.ffmpeg.format = 'MPEG4'
            kbps = int(pixels/230)
            maxkbps = kbps*1.2
            scene.render.ffmpeg.maxrate = maxkbps
            scene.render.ffmpeg.video_bitrate = kbps
            scene.render.ffmpeg.audio_codec = 'NONE'
        elif setting == 'JPEG':
            scene.render.image_settings.file_format = 'JPEG'
            scene.render.image_settings.color_mode = 'RGB'
            scene.render.image_settings.quality = 95
        elif setting == 'PNG':
            scene.render.image_settings.file_format = 'PNG'
            if transparent:
                scene.render.image_settings.color_mode = 'RGBA'
            else:
                scene.render.image_settings.color_mode = 'RGB'
            scene.render.image_settings.color_depth = '8'
            scene.render.image_settings.compression = 90
        elif setting == 'TIFF':
            scene.render.image_settings.file_format = 'TIFF'
            if transparent:
                scene.render.image_settings.color_mode = 'RGBA'
            else:
                scene.render.image_settings.color_mode = 'RGB'
            scene.render.image_settings.color_depth = '16'
            scene.render.image_settings.tiff_codec = 'DEFLATE'
        elif setting == 'EXR':
            scene.render.image_settings.file_format = 'OPEN_EXR'
            if transparent:
                scene.render.image_settings.color_mode = 'RGBA'
            else:
                scene.render.image_settings.color_mode = 'RGB'
            scene.render.image_settings.color_depth = '32'
            scene.render.image_settings.exr_codec = 'ZIP'

    def render_sequence(self, sequence):
        """Begins rendering process: creates a temporary scene, sets it up, copies the sequence to the temporary scene, and begins rendering
        Arguments:
            sequence: VSE Sequence object to begin rendering"""

        self.rendering = True
        self.rendering_sequence = sequence
        self.original_scene = bpy.context.scene
        original_start = sequence.frame_final_start
        original_end = sequence.frame_final_end
        original_channel = sequence.channel
        bpy.ops.sequencer.select_all(action='SELECT')
        bpy.ops.sequencer.copy()

        #create a temporary scene
        bpy.ops.scene.new(type='EMPTY')
        self.rendering_scene = bpy.context.scene
        self.rendering_scene_name = self.rendering_scene.name

        #copy sequence to new scene and set up scene
        bpy.ops.sequencer.paste()
        bpy.ops.sequencer.select_all(action='SELECT')
        for seq in self.rendering_scene.sequence_editor.sequences:
            if seq.frame_final_start == original_start and seq.frame_final_end == original_end and seq.channel == original_channel:
                seq.select = False
        bpy.ops.sequencer.delete()

        temp_sequence = self.rendering_scene.sequence_editor.sequences[0]
        copy_curves(sequence, temp_sequence, self.original_scene, self.rendering_scene)
        self.rendering_scene.frame_start = temp_sequence.frame_final_start
        self.rendering_scene.frame_end = temp_sequence.frame_final_end - 1
        filename = sequence.name
        if self.original_scene.quick_batch.batch_render_directory:
            path = self.original_scene.quick_batch.batch_render_directory
        else:
            path = self.rendering_scene.render.filepath
        self.rendering_scene.render.filepath = os.path.join(path, filename)

        #render
        if sequence.type != 'SOUND':
            if sequence.blend_type in ['OVER_DROP', 'ALPHA_OVER']:
                transparent = True
                setting = self.original_scene.quick_batch.transparent_settings_menu
            else:
                transparent = False
                setting = self.original_scene.quick_batch.video_settings_menu
            self.set_render_settings(self.rendering_scene, setting, transparent)

            if not self.original_scene.quick_batch.batch_effects:
                temp_sequence.modifiers.clear()
            self.file = self.rendering_scene.render.frame_path(frame=1)
            bpy.ops.render.render('INVOKE_DEFAULT', animation=True)
            self.rendering_scene.quick_batch.batch_rendering = True
            if 'batch_render_complete_handler' not in str(bpy.app.handlers.render_complete):
                bpy.app.handlers.render_complete.append(batch_render_complete_handler)
            if 'batch_render_cancel_handler' not in str(bpy.app.handlers.render_cancel):
                bpy.app.handlers.render_cancel.append(batch_render_cancel_handler)
            if self._timer:
                bpy.context.window_manager.event_timer_remove(self._timer)
            self._timer = bpy.context.window_manager.event_timer_add(1, bpy.context.window)
        else:
            audio_format = self.original_scene.quick_batch.audio_settings_menu
            if audio_format == 'FLAC':
                extension = '.flac'
                container = 'FLAC'
                codec = 'FLAC'
            elif audio_format == 'MP3':
                extension = '.mp3'
                container = 'MP3'
                codec = 'MP3'
            elif audio_format == 'OGG':
                extension = '.ogg'
                container = 'OGG'
                codec = 'VORBIS'
            else:  #audio_format == 'WAV'
                extension = '.wav'
                container = 'WAV'
                codec = 'PCM'
            bpy.ops.sound.mixdown(filepath=self.rendering_scene.render.filepath+extension, format='S16', bitrate=192, container=container, codec=codec)
            self.file = self.rendering_scene.render.filepath+extension
            self.rendering_scene.quick_batch.batch_rendering = False
            if self._timer:
                bpy.context.window_manager.event_timer_remove(self._timer)
            self._timer = bpy.context.window_manager.event_timer_add(1, bpy.context.window)

    def copy_settings(self, sequence, new_sequence):
        """Copies the needed settings from the original sequence to the newly imported sequence
        Arguments:
            sequence: VSE Sequence, the original
            new_sequence: VSE Sequence, the sequence to copy the settings to"""

        new_sequence.lock = sequence.lock
        if hasattr(sequence, 'parent'):
            new_sequence.parent = sequence.parent
        new_sequence.blend_alpha = sequence.blend_alpha
        new_sequence.blend_type = sequence.blend_type
        if new_sequence.type != 'SOUND':
            new_sequence.alpha_mode = sequence.alpha_mode

    def finish_render(self):
        """Finishes the process of rendering a sequence by replacing the original sequence, and deleting the temporary scene"""
        bpy.context.screen.scene = self.rendering_scene
        try:
            bpy.ops.render.view_cancel()
        except:
            pass
        if self.rendering_sequence.type != 'SOUND':
            file_format = self.rendering_scene.render.image_settings.file_format
            if file_format in ['AVI_JPEG', 'AVI_RAW', 'FRAMESERVER', 'H264', 'FFMPEG', 'THEORA', 'XVID']:
                #delete temporary scene
                bpy.ops.scene.delete()
                bpy.context.screen.scene = self.original_scene
                new_sequence = self.original_scene.sequence_editor.sequences.new_movie(name=self.rendering_sequence.name+' rendered', filepath=self.file, channel=self.rendering_sequence.channel, frame_start=self.rendering_sequence.frame_final_start)
            else:
                files = []
                for frame in range(2, self.rendering_scene.frame_end):
                    files.append(os.path.split(self.rendering_scene.render.frame_path(frame=frame))[1])
                #delete temporary scene
                bpy.ops.scene.delete()
                bpy.context.screen.scene = self.original_scene
                new_sequence = self.original_scene.sequence_editor.sequences.new_image(name=self.rendering_sequence.name+' rendered', filepath=self.file, channel=self.rendering_sequence.channel, frame_start=self.rendering_sequence.frame_final_start)
                for file in files:
                    new_sequence.elements.append(file)
        else:
            #delete temporary scene
            bpy.ops.scene.delete()
            bpy.context.screen.scene = self.original_scene

            new_sequence = self.original_scene.sequence_editor.sequences.new_sound(name=self.rendering_sequence.name+' rendered', filepath=self.file, channel=self.rendering_sequence.channel, frame_start=self.rendering_sequence.frame_final_start)
        #replace sequence
        bpy.ops.sequencer.select_all(action='DESELECT')
        self.copy_settings(self.rendering_sequence, new_sequence)
        self.rendering_sequence.select = True
        new_sequence.select = True
        self.original_scene.sequence_editor.active_strip = self.rendering_sequence

        for other_sequence in self.original_scene.sequence_editor.sequences_all:
            if hasattr(other_sequence, 'input_1'):
                if other_sequence.input_1 == self.rendering_sequence:
                    other_sequence.input_1 = new_sequence
            if hasattr(other_sequence, 'input_2'):
                if other_sequence.input_2 == self.rendering_sequence:
                    other_sequence.input_2 = new_sequence
        if not self.original_scene.quick_batch.batch_effects:
            bpy.ops.sequencer.strip_modifier_copy(type='REPLACE')

        new_sequence.select = False
        bpy.ops.sequencer.delete()

    def next_render(self):
        """Starts rendering the next sequence in the list"""

        sequence = self.renders.pop(0)
        print('rendering '+sequence.name)
        self.render_sequence(sequence)

    def modal(self, context, event):
        """Main modal function, handles the render list"""

        if not self.rendering_scene:
            if self._timer:
                context.window_manager.event_timer_remove(self._timer)
                self._timer = None
            return {'CANCELLED'}
        if not bpy.data.scenes.get(self.rendering_scene_name, False):
            #the user deleted the rendering scene, uh-oh... blender will crash now.
            if self._timer:
                context.window_manager.event_timer_remove(self._timer)
                self._timer = None
            return {'CANCELLED'}
        if event.type == 'TIMER':
            if not self.rendering_scene.quick_batch.batch_rendering:
                if self._timer:
                    context.window_manager.event_timer_remove(self._timer)
                    self._timer = None
                self.finish_render()
                if len(self.renders) > 0:
                    self.next_render()
                    self.report({'INFO'}, "Rendered "+str(self.total_renders - len(self.renders))+" out of "+str(self.total_renders)+" files.  "+str(self.total_frames)+" frames total.")
                else:
                    return {'FINISHED'}

            return {'PASS_THROUGH'}
        if self.rendering_scene.quick_batch.batch_rendering_cancel:
            if self._timer:
                context.window_manager.event_timer_remove(self._timer)
                self._timer = None
            self.renders.clear()
            try:
                bpy.ops.render.view_cancel()
            except:
                pass
            try:
                self.rendering_scene.user_clear()
                bpy.data.scenes.remove(self.rendering_scene)
                context.screen.scene = self.original_scene
                context.screen.scene.update()
                context.window_manager.update_tag()
            except:
                pass
            return {'CANCELLED'}
        return {'PASS_THROUGH'}

    def invoke(self, context, event):
        """Called when the batch render is initialized.  Sets up variables and begins the rendering process."""

        del event
        context.window_manager.modal_handler_add(self)
        self.rendering = False
        oldscene = context.scene
        quick_batch = oldscene.quick_batch
        name = oldscene.name + ' Batch Render'
        bpy.ops.scene.new(type='FULL_COPY')
        newscene = context.scene
        newscene.name = name

        if quick_batch.batch_meta == 'SUBSTRIPS':
            old_sequences = newscene.sequence_editor.sequences_all
        else:
            old_sequences = newscene.sequence_editor.sequences

        #queue up renders
        self.total_frames = 0
        self.audio_frames = 0
        self.renders = []
        for sequence in old_sequences:
            if (quick_batch.batch_selected and sequence.select) or not quick_batch.batch_selected:
                if sequence.type == 'MOVIE' or sequence.type == 'IMAGE' or sequence.type == 'MOVIECLIP':
                    #standard video or image sequence
                    self.renders.append(sequence)
                    self.total_frames = self.total_frames + sequence.frame_final_duration
                elif sequence.type == 'SOUND':
                    #audio sequence
                    if quick_batch.batch_audio:
                        self.renders.append(sequence)
                        self.audio_frames = self.audio_frames + sequence.frame_final_duration
                elif sequence.type == 'META':
                    #meta sequence
                    if quick_batch.batch_meta == 'SINGLESTRIP':
                        self.renders.append(sequence)
                        self.total_frames = self.total_frames + sequence.frame_final_duration
                else:
                    #other sequence type, not handled
                    pass
        self.total_renders = len(self.renders)
        if self.total_renders > 0:
            self.next_render()
            return {'RUNNING_MODAL'}
        else:
            return {'CANCELLED'}


class QuickBatchRenderSetting(bpy.types.PropertyGroup):
    """Property group to store most VSEQF settings.  This will be assigned to scene.quick_batch"""
    video_settings_menu = bpy.props.EnumProperty(
        name="Video Render Setting",
        default='DEFAULT',
        items=[('DEFAULT', 'Scene Settings', '', 1), ('AVIJPEG', 'AVI JPEG', '', 2), ('H264', 'H264 Video', '', 3), ('JPEG', 'JPEG Sequence', '', 4), ('PNG', 'PNG Sequence', '', 5), ('TIFF', 'TIFF Sequence', '', 6), ('EXR', 'Open EXR Sequence', '', 7)])
    transparent_settings_menu = bpy.props.EnumProperty(
        name="Transparent Video Render Setting",
        default='DEFAULT',
        items=[('DEFAULT', 'Scene Settings', '', 1), ('AVIJPEG', 'AVI JPEG (No Transparency)', '', 2), ('H264', 'H264 Video (No Transparency)', '', 3), ('JPEG', 'JPEG Sequence (No Transparency)', '', 4), ('PNG', 'PNG Sequence', '', 5), ('TIFF', 'TIFF Sequence', '', 6), ('EXR', 'Open EXR Sequence', '', 7)])
    audio_settings_menu = bpy.props.EnumProperty(
        name="Audio Render Setting",
        default='FLAC',
        #mp3 export seems to be broken currently, (exports as extremely loud distorted garbage) so "('MP3', 'MP3 File', '', 4), " is removed for now
        items=[('FLAC', 'FLAC Audio', '', 1), ('WAV', 'WAV File', '', 2), ('OGG', 'OGG File', '', 3)])

    batch_render_directory = bpy.props.StringProperty(
        name="Render Directory",
        default='./',
        description="Folder to batch render strips to.",
        subtype='DIR_PATH')
    batch_selected = bpy.props.BoolProperty(
        name="Render Only Selected",
        default=False)
    batch_effects = bpy.props.BoolProperty(
        name="Render Modifiers",
        default=True,
        description="If active, this will render modifiers to the export, if deactivated, modifiers will be copied.")
    batch_audio = bpy.props.BoolProperty(
        name="Render Audio",
        default=True,
        description="If active, this will render audio strips to a new file, if deactivated, audio strips will be copied over.")
    batch_meta = bpy.props.EnumProperty(
        name="Render Meta Strips",
        default='SINGLESTRIP',
        items=[('SINGLESTRIP', 'Single Strip', '', 1), ('SUBSTRIPS', 'Individual Substrips', '', 2), ('IGNORE', 'Ignore', '', 3)])
    batch_rendering = bpy.props.BoolProperty(
        name="Currently Rendering File",
        default=False)
    batch_rendering_cancel = bpy.props.BoolProperty(
        name="Canceled A Render",
        default=False)


#Register properties, operators, menus and shortcuts
classes = (QuickBatchRender, QuickBatchRenderPanel, QuickBatchRenderSetting)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Scene.quick_batch = bpy.props.PointerProperty(type=QuickBatchRenderSetting)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
