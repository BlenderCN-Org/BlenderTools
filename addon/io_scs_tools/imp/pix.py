# ##### BEGIN GPL LICENSE BLOCK #####
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software Foundation,
# Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

# Copyright (C) 2013-2014: SCS Software

import bpy
import os
from io_scs_tools.internals import inventory as _inventory
from io_scs_tools.utils import get_scs_globals as _get_scs_globals
from io_scs_tools.utils import material as _material_utils
from io_scs_tools.utils import name as _name_utils
from io_scs_tools.utils import object as _object_utils
from io_scs_tools.utils.printout import lprint

from io_scs_tools.imp import pia as _pia
from io_scs_tools.imp import pic as _pic
from io_scs_tools.imp import pim as _pim
from io_scs_tools.imp import pip as _pip
from io_scs_tools.imp import pis as _pis
from io_scs_tools.imp import pit as _pit


def _get_shader_data(material_data):
    """Returns Material's Effect, Attributes and Textures.

    :param material_data: Material data
    :type material_data: list
    :return: Material's Effect, Attributes, Textures
    :rtype: tuple
    """
    material_effect = material_data[0]
    material_attributes = material_data[2]
    material_textures = material_data[3]
    material_section = material_data[4]
    return material_effect, material_attributes, material_textures, material_section


def _find_preset(material_effect):
    """Tries to find suitable Shader Preset (as defined in shader_presets.txt file) for imported shader. If it cannot be found, it will return None.

    :param material_effect: Name of the requested Look
    :type material_effect: str
    :return: Preset index and name or None
    :rtype: (int, str) | None
    """

    scs_shader_presets_inventory = bpy.context.scene.scs_shader_presets_inventory
    for i, shader_preset in enumerate(scs_shader_presets_inventory):

        if shader_preset.name != "<none>":
            preset_section = _material_utils.get_shader_preset(_get_scs_globals().shader_presets_filepath, shader_preset.name)
            for preset_prop in preset_section.props:
                if preset_prop[0] == "Effect":

                    if preset_prop[1] == material_effect:

                        return i, shader_preset.name

    return None, None


def _create_scs_root_object(name, loaded_variants, loaded_looks, mats_info, objects, skinned_objects, locators, armature):
    """Creates an 'SCS Root Object' (Empty Object) for currently imported
    'SCS Game Object' and parent all import content to it.

    :param name:
    :type name: str
    :param loaded_variants: X
    :type loaded_variants: list
    :param loaded_looks: X
    :type loaded_looks: list
    :param mats_info: list of material info, one material info consists of list: [ blend_mat_name, mat_effect, original_mat_alias ]
    :type mats_info: list of list
    :param objects: X
    :type objects: list
    :param skinned_objects: X
    :type skinned_objects: list
    :param locators: X
    :type locators: list
    :param armature: Armature Object
    :type armature: bpy.types.Object
    :return: SCS Root Object
    :rtype: bpy.types.Object
    """

    context = bpy.context

    # MAKE THE 'SCS ROOT OBJECT' NAME UNIQUE
    if name in bpy.data.objects:
        name = _name_utils.make_unique_name(bpy.data.objects[0], name)

    # CREATE EMPTY OBJECT
    bpy.ops.object.empty_add(
        view_align=False,
        location=(0.0, 0.0, 0.0),
        # rotation=rot,
    )  # , layers=(False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False,
    # False, False))

    # MAKE A PROPER SETTINGS TO THE 'SCS Game Object' OBJECT
    scs_root_object = context.active_object
    scs_root_object.name = name
    scs_root_object.scs_props.scs_root_object_export_enabled = True
    scs_root_object.scs_props.empty_object_type = 'SCS_Root'

    # print('LOD.pos: %s' % str(scs_root_object.location))
    # print('CUR.pos: %s' % str(context.space_data.cursor_location))

    # PARENTING
    if armature:
        # print('ARM.pos: %s' % str(armature.location))
        bpy.ops.object.select_all(action='DESELECT')
        armature.select = True
        bpy.ops.object.parent_set(type='OBJECT', keep_transform=False)
        armature.scs_props.parent_identity = scs_root_object.name

    for obj in objects:
        if obj not in skinned_objects:
            # print('OBJ.pos: %s' % str(object.location))
            bpy.ops.object.select_all(action='DESELECT')
            obj.select = True
            bpy.ops.object.parent_set(type='OBJECT', keep_transform=False)
            obj.scs_props.parent_identity = scs_root_object.name

    for obj in locators:
        bpy.ops.object.select_all(action='DESELECT')
        obj.select = True
        bpy.ops.object.parent_set(type='OBJECT', keep_transform=False)
        obj.scs_props.parent_identity = scs_root_object.name

    # LOCATION
    scs_root_object.location = context.scene.cursor_location

    # MAKE ONLY 'SCS GAME OBJECT' SELECTED
    bpy.ops.object.select_all(action='DESELECT')
    for obj in bpy.data.objects:
        obj.select = False
    scs_root_object.select = True
    context.scene.objects.active = scs_root_object

    # MAKE PART RECORD
    part_inventory = scs_root_object.scs_object_part_inventory
    for part_name in _object_utils.collect_parts_on_root(scs_root_object):
        _inventory.add_item(part_inventory, part_name)

    # MAKE VARIANT RECORD
    variant_inventory = scs_root_object.scs_object_variant_inventory
    for variant_record in loaded_variants:
        variant_name = variant_record[0]
        variantparts = variant_record[1]

        variant = _inventory.add_item(variant_inventory, variant_name)

        # fore every variant create all of the part entries and mark them included properly
        for part in part_inventory:

            part = _inventory.add_item(variant.parts, part.name)
            if part.name in variantparts:
                part.include = True
            else:
                part.include = False

    # MAKE LOOK RECORDS
    for look_i, look in enumerate(loaded_looks):

        look_name = look[0]
        look_mat_settings = look[1]

        # SETUP ALL THE MATERIALS, NOTE: They should be already created by PIM import.
        for mat_info in mats_info:
            mat = bpy.data.materials[mat_info[0]]
            if mat_info[2] in look_mat_settings:

                # ASSIGN IMPORTED SHADER DATA
                material_effect, material_attributes, material_textures, material_section = _get_shader_data(look_mat_settings[mat_info[2]])

                # TRY TO FIND SUITABLE PRESET
                (preset_index, preset_name) = _find_preset(material_effect)

                if preset_index:  # preset name is found within presets shaders

                    mat.scs_props.active_shader_preset_name = preset_name
                    preset_section = _material_utils.get_shader_preset(_get_scs_globals().shader_presets_filepath, preset_name)

                    if preset_section:

                        preset_effect = preset_section.get_prop_value("Effect")
                        mat.scs_props.mat_effect_name = preset_effect

                        if look_i == 0:
                            # apply default shader settings
                            _material_utils.set_shader_data_to_material(mat, preset_section, preset_effect,
                                                                        is_import=True)

                        # reapply settings from material
                        _material_utils.set_shader_data_to_material(mat, material_section, material_effect,
                                                                    is_import=True, override_back_data=False)

                        lprint("I Using shader preset on material %r.", (mat.name,))

                    else:
                        print('''NO "preset_section"! (Shouldn't happen!)''')

                else:  # import shader directly from material and mark it as imported

                    mat.scs_props.active_shader_preset_name = "<imported>"
                    _material_utils.set_shader_data_to_material(mat, material_section, material_effect,
                                                                is_import=True)

                    lprint("I Using imported shader on material %r.", (mat.name,))

                if look_i == len(loaded_looks) - 1:
                    # delete not needed data on material
                    if "scs_tex_aliases" in mat:
                        del mat["scs_tex_aliases"]

        # CREATE NEW LOOK ENTRY ON ROOT
        bpy.ops.object.add_scs_look(look_name=look_name, instant_apply=False)

    # apply first look after everything is done
    scs_root_object.scs_props.active_scs_look = 0

    # fix scs root children objects count so it won't trigger persistent cycle
    scs_root_object.scs_cached_num_children = len(scs_root_object.children)

    return scs_root_object


def load(context, filepath):
    """

    :param context: Blender Context currently used for window_manager.update_progress and bpy_object_utils.object_data_add
    :type context: bpy.types.Context
    :param filepath: File path to be imported
    :type filepath: str
    :return: Return state statuses (Usually 'FINISHED')
    :rtype: dict
    """
    import time

    t = time.time()
    bpy.context.window.cursor_modal_set('WAIT')
    # import_scale = _get_scs_globals().import_scale
    # load_textures = _get_scs_globals().load_textures
    # mesh_creation_type = _get_scs_globals().mesh_creation_type
    scs_globals = _get_scs_globals()
    dump_level = int(scs_globals.dump_level)
    lprint("", report_errors=-1, report_warnings=-1)  # Clear the 'error_messages' and 'warning_messages'

    collision_locators = []
    prefab_locators = []
    loaded_variants = []
    loaded_looks = []
    objects = []
    skinned_objects = []
    locators = []
    mats_info = []
    scs_root_object = skeleton = bones = armature = None

    # ## NEW SCENE CREATION
    # if _get_scs_globals().scs_lod_definition_type == 'scenes':
    # if context.scene.name != 'Scene':
    # bpy.ops.scene.new(type='NEW')

    # IMPORT PIM
    if scs_globals.import_pim_file or scs_globals.import_pis_file:
        if filepath:
            if os.path.isfile(filepath):
                lprint('\nD PIM filepath:\n  %s', (filepath.replace("\\", "/"),))
                result, objects, skinned_objects, locators, armature, skeleton, mats_info = _pim.load(context, filepath)
                # print('  armature:\n%s\n  skeleton:\n%s' % (str(armature), str(skeleton)))
            else:
                lprint('\nI No file found at %r!' % (filepath.replace("\\", "/"),))
        else:
            lprint('\nI No filepath provided!')

    # IMPORT PIT
    bpy.context.scene.objects.active = None
    if scs_globals.import_pit_file:
        pit_filepath = str(filepath[:-1] + 't')
        if os.path.isfile(pit_filepath):
            lprint('\nD PIT filepath:\n  %s', (pit_filepath,))
            # print('PIT filepath:\n  %s' % pit_filepath)
            result, loaded_variants, loaded_looks = _pit.load(pit_filepath)
        else:
            lprint('\nI No PIT file.')
            # print('INFO - No PIT file.')

    # IMPORT PIC
    if scs_globals.import_pic_file:
        pic_filepath = str(filepath[:-1] + 'c')
        if os.path.isfile(pic_filepath):
            lprint('\nD PIC filepath:\n  %s', (pic_filepath,))
            # print('PIC filepath:\n  %s' % pic_filepath)
            result, collision_locators = _pic.load(pic_filepath)
        else:
            lprint('\nI No PIC file.')
            # print('INFO - No PIC file.')

    # IMPORT PIP
    if scs_globals.import_pip_file:
        pip_filepath = str(filepath[:-1] + 'p')
        if os.path.isfile(pip_filepath):
            lprint('\nD PIP filepath:\n  %s', (pip_filepath,))
            # print('PIP filepath:\n  %s' % pip_filepath)
            result, prefab_locators = _pip.load(pip_filepath)
        else:
            lprint('\nI No PIP file.')
            # print('INFO - No PIP file.')

    # SETUP 'SCS GAME OBJECTS'
    for item in collision_locators:
        locators.append(item)
    for item in prefab_locators:
        locators.append(item)
    path, file = os.path.split(filepath)
    # print('  path: %r\n  file: %r' % (path, file))
    lod_name, ext = os.path.splitext(file)
    if objects or locators or (armature and skeleton):
        scs_root_object = _create_scs_root_object(lod_name, loaded_variants, loaded_looks, mats_info, objects, skinned_objects, locators, armature)

    # IMPORT PIS
    if scs_globals.import_pis_file:
        pis_filepath = str(filepath[:-1] + 's')
        if os.path.isfile(pis_filepath):
            lprint('\nD PIS filepath:\n  %s', (pis_filepath,))
            # print('PIS filepath:\n  %s' % pis_filepath)
            bones = _pis.load(pis_filepath, armature)
        else:
            bones = None
            lprint('\nI No PIS file.')
            # print('INFO - No PIS file.')

    # IMPORT PIA
    if scs_globals.import_pis_file and scs_globals.import_pia_file:
        basepath = os.path.dirname(filepath)
        # Search for PIA files in model's directory and its subdirectiories...
        lprint('\nD Searching the directory for PIA files:\n   %s', (basepath,))
        # print('\nSearching the directory for PIA files:\n   %s' % str(basepath))
        pia_files = []
        index = 0
        for root, dirs, files in os.walk(basepath):
            if not scs_globals.include_subdirs_for_pia:
                if index > 0:
                    break
            # print('  root: %s - dirs: %s - files: %s' % (str(root), str(dirs), str(files)))
            for file in files:
                if file.endswith(".pia"):
                    pia_filepath = os.path.join(root, file)
                    pia_files.append(pia_filepath)
            index += 1

        if len(pia_files) > 0:
            lprint('D PIA files found:')
            for pia_filepath in pia_files:
                lprint('D %r', pia_filepath)
            # print('armature: %s\nskeleton: %r\nbones: %s\n' % (str(armature), str(skeleton), str(bones)))
            _pia.load(scs_root_object, pia_files, armature, skeleton, bones)
        else:
            lprint('\nI No PIA files.')

            # ## SETUP 'SCS GAME OBJECTS'
            # for item in collision_locators:
            # locators.append(item)
            # for item in prefab_locators:
            # locators.append(item)
            # path, file = os.path.split(filepath)
            # print('  path: %r\n  file: %r' % (path, file))
            # lod_name, ext = os.path.splitext(file)
            # if objects:
            # scs_root_object = create_scs_root_object(lod_name, loaded_variants, objects, skinned_objects, locators, armature)

            # SET OPTIMAL SETTINGS AND DRAW MODES

    # fix scene objects count so it won't trigger copy cycle
    bpy.context.scene.scs_cached_num_objects = len(bpy.context.scene.objects)

    # Turn on Textured Solid in 3D view...
    for bl_screen in bpy.data.screens:
        for bl_area in bl_screen.areas:
            for bl_space in bl_area.spaces:
                if bl_space.type == 'VIEW_3D':
                    bl_space.show_textured_solid = True

    # Turn on GLSL in 3D view...
    bpy.context.scene.game_settings.material_mode = 'GLSL'

    # Turn on "Frame Dropping" for animation playback...
    bpy.context.scene.use_frame_drop = True

    # FINAL FEEDBACK
    bpy.context.window.cursor_modal_restore()
    lprint('\nI Import compleeted in %.3f sec.', time.time() - t, report_errors=True, report_warnings=True)
    return True