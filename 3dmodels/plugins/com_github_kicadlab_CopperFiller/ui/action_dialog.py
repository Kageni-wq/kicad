import wx
import wx.xrc

import json
import os

from typing import List, Dict

from .color import create_layer_colors_from_json

FRAME_WIDTH = 400
FRAME_HEIGHT = 550

###########################################################################
## Class CopperFillerDialog
###########################################################################

class CopperFillerDialog ( wx.Dialog ):

    def __init__( self, parent, active_layers: List, board_class: Dict, settings: str, colors: str ):
        width, height = wx.GetDisplaySize()
        wx.Dialog.__init__ ( 
            self, 
            parent, 
            id = wx.ID_ANY, 
            title = _(u"Settings CopperFiller"), 
            pos = wx.DefaultPosition, 
            size = wx.Size( FRAME_WIDTH*max(1, width // 1920), FRAME_HEIGHT*max(1, height // 1080) ), 
            style = wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER
            )
        
        self.board_class = board_class
        self.settings_file = settings

        json_color = dict()
        with open(colors, 'r') as f:
            json_color = json.load(f)
        
        self.layer_colors = create_layer_colors_from_json(json_color, active_layers)
        self.default_layer_color = wx.Colour(255, 255, 255)  # Белый

        self.SetSizeHints( wx.DefaultSize, wx.DefaultSize )

        main_sizer = wx.BoxSizer( wx.VERTICAL )

        layer_sizer = wx.StaticBoxSizer( wx.HORIZONTAL, self, _(u"Layer") )

        self.layer_color = wx.StaticText( layer_sizer.GetStaticBox(), wx.ID_ANY, u"\u2588", wx.DefaultPosition, wx.DefaultSize, 0 )
        self.layer_color.Wrap( -1 )

        layer_sizer.Add( self.layer_color, 0, wx.ALIGN_CENTER|wx.ALL, 5 )

        layer_choiceChoices = active_layers
        self.layer_choice = wx.ComboBox( layer_sizer.GetStaticBox(), wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.DefaultSize, layer_choiceChoices, 0 )
        self.layer_choice.SetSelection( 0 )
        layer_sizer.Add( self.layer_choice, 1, wx.ALIGN_CENTER|wx.ALL, 5 )

        main_sizer.Add( layer_sizer, 1, wx.ALL|wx.EXPAND, 5 )

        element_sizer = wx.StaticBoxSizer( wx.HORIZONTAL, self, _(u"Element") )

        self.shape_label = wx.StaticText( element_sizer.GetStaticBox(), wx.ID_ANY, _(u"Shape:"), wx.DefaultPosition, wx.DefaultSize, 0 )
        self.shape_label.Wrap( -1 )

        element_sizer.Add( self.shape_label, 0, wx.ALIGN_CENTER|wx.ALL, 5 )

        shape_choiceChoices = [ _(u"Square"), _(u"Circle") ]
        self.shape_choice = wx.ComboBox( element_sizer.GetStaticBox(), wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.DefaultSize, shape_choiceChoices, 0 )
        self.shape_choice.SetSelection( 0 )
        element_sizer.Add( self.shape_choice, 1, wx.ALIGN_CENTER|wx.ALL, 5 )

        self.staticline1 = wx.StaticLine( element_sizer.GetStaticBox(), wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.LI_VERTICAL )
        element_sizer.Add( self.staticline1, 0, wx.EXPAND | wx.ALL, 5 )

        self.size_label = wx.StaticText( element_sizer.GetStaticBox(), wx.ID_ANY, _(u"Size:"), wx.DefaultPosition, wx.DefaultSize, 0 )
        self.size_label.Wrap( -1 )

        element_sizer.Add( self.size_label, 0, wx.ALIGN_CENTER|wx.ALL, 5 )

        self.size_spinCtrlDouble = wx.SpinCtrlDouble( element_sizer.GetStaticBox(), wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.DefaultSize, wx.SP_ARROW_KEYS, 0.6, 2.0, 0.6, 0.1 )
        self.size_spinCtrlDouble.SetDigits( 1 )
        element_sizer.Add( self.size_spinCtrlDouble, 0, wx.ALIGN_CENTER|wx.ALL, 5 )


        main_sizer.Add( element_sizer, 1, wx.ALL|wx.EXPAND, 5 )

        pattern_sizer = wx.StaticBoxSizer( wx.VERTICAL, self, _(u"Geometry") )

        density_sizer = wx.BoxSizer( wx.HORIZONTAL )

        self.density_label = wx.StaticText( pattern_sizer.GetStaticBox(), wx.ID_ANY, _(u"Density:"), wx.DefaultPosition, wx.DefaultSize, 0 )
        self.density_label.Wrap( -1 )

        density_sizer.Add( self.density_label, 0, wx.ALIGN_CENTER|wx.ALL, 5 )

        self.density_slider = wx.Slider( pattern_sizer.GetStaticBox(), wx.ID_ANY, 50, 25, 90, wx.DefaultPosition, wx.DefaultSize, wx.SL_HORIZONTAL|wx.SL_MIN_MAX_LABELS )
        density_sizer.Add( self.density_slider, 1, wx.ALL, 5 )

        self.density_spinCtrl = wx.SpinCtrl( pattern_sizer.GetStaticBox(), wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.DefaultSize, wx.SP_ARROW_KEYS, 25, 90, 50 )
        density_sizer.Add( self.density_spinCtrl, 0, wx.ALIGN_CENTER|wx.ALL, 5 )


        pattern_sizer.Add( density_sizer, 1, wx.ALIGN_CENTER|wx.ALL|wx.EXPAND, 5 )

        offest_sizer = wx.BoxSizer( wx.HORIZONTAL )

        self.offset_x_label = wx.StaticText( pattern_sizer.GetStaticBox(), wx.ID_ANY, _(u"Offset X:"), wx.DefaultPosition, wx.DefaultSize, 0 )
        self.offset_x_label.Wrap( -1 )

        offest_sizer.Add( self.offset_x_label, 0, wx.ALIGN_CENTER|wx.ALL, 5 )

        self.offset_spinCtrlDouble = wx.SpinCtrlDouble( pattern_sizer.GetStaticBox(), wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.DefaultSize, wx.SP_ARROW_KEYS, 0.0, 5.0, 0.0, 0.1 )
        self.offset_spinCtrlDouble.SetDigits( 1 )
        offest_sizer.Add( self.offset_spinCtrlDouble, 0, wx.ALIGN_CENTER|wx.ALL, 5 )

        self.m_staticline2 = wx.StaticLine( pattern_sizer.GetStaticBox(), wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.LI_VERTICAL )
        offest_sizer.Add( self.m_staticline2, 0, wx.EXPAND | wx.ALL, 5 )

        self.offset_y_label = wx.StaticText( pattern_sizer.GetStaticBox(), wx.ID_ANY, _(u"Offset Y:"), wx.DefaultPosition, wx.DefaultSize, 0 )
        self.offset_y_label.Wrap( -1 )

        offest_sizer.Add( self.offset_y_label, 0, wx.ALIGN_CENTER|wx.ALL, 5 )

        self.offset_y_spinCtrlDouble = wx.SpinCtrlDouble( pattern_sizer.GetStaticBox(), wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.DefaultSize, wx.SP_ARROW_KEYS, 0.0, 5.0, 0.0, 0.1 )
        self.offset_y_spinCtrlDouble.SetDigits( 1 )
        offest_sizer.Add( self.offset_y_spinCtrlDouble, 0, wx.ALIGN_CENTER|wx.ALL, 5 )


        pattern_sizer.Add( offest_sizer, 1, wx.ALIGN_CENTER|wx.ALL|wx.EXPAND, 5 )


        main_sizer.Add( pattern_sizer, 1, wx.EXPAND, 5 )

        class_sizer = wx.StaticBoxSizer( wx.VERTICAL, self, _(u"Board Class | Clearance Settings") )

        class_clearance_sizer = wx.BoxSizer( wx.VERTICAL )

        class_choiceChoices = [_('Board Class {i}').format(i=i+1) for i in range(self.board_class['ClassCount'])]
        self.class_choice = wx.ComboBox( class_sizer.GetStaticBox(), wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.DefaultSize, class_choiceChoices, 0 )
        self.class_choice.SetSelection( 0 )
        class_clearance_sizer.Add( self.class_choice, 1, wx.ALIGN_CENTER|wx.EXPAND|wx.ALL, 5 )

        clearance_sizer = wx.BoxSizer( wx.HORIZONTAL )

        self.clearance_label = wx.StaticText( class_sizer.GetStaticBox(), wx.ID_ANY, _(u"Element Clearance:"), wx.DefaultPosition, wx.DefaultSize, 0 )
        self.clearance_label.Wrap( self.clearance_label.GetSize().width - 5 )
        clearance_sizer.Add( self.clearance_label, 0, wx.ALIGN_CENTER|wx.ALL, 5 )

        self.clearance_spinCtrlDouble = wx.SpinCtrlDouble( class_sizer.GetStaticBox(), wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.DefaultSize, wx.SP_ARROW_KEYS, 0.00, 3.00, 0.00, 0.01 )
        self.clearance_spinCtrlDouble.SetDigits( 2 )
        clearance_sizer.Add( self.clearance_spinCtrlDouble, 0, wx.ALIGN_CENTER|wx.ALL, 5 )

        self.m_staticline3 = wx.StaticLine( class_sizer.GetStaticBox(), wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.LI_VERTICAL )
        clearance_sizer.Add( self.m_staticline3, 0, wx.ALIGN_CENTER|wx.ALL|wx.EXPAND, 5 )

        self.clearance_label_2 = wx.StaticText( class_sizer.GetStaticBox(), wx.ID_ANY, _(u"Conductor and Element Clearance:"), wx.DefaultPosition, wx.DefaultSize, 0 )
        self.clearance_label_2.Wrap( self.clearance_label_2.GetSize().width - 20 )

        clearance_sizer.Add( self.clearance_label_2, 1, wx.ALIGN_CENTER|wx.ALL, 5 )

        self.clearance_spinCtrlDouble_2 = wx.SpinCtrlDouble( class_sizer.GetStaticBox(), wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.DefaultSize, wx.SP_ARROW_KEYS, 0.6, 5.0, 0.6, 0.1 )
        self.clearance_spinCtrlDouble_2.SetDigits( 1 )
        clearance_sizer.Add( self.clearance_spinCtrlDouble_2, 1, wx.ALIGN_CENTER|wx.ALL, 5 )

        class_clearance_sizer.Add( clearance_sizer, 1, wx.EXPAND, 5 )       

        class_sizer.Add( class_clearance_sizer, 0, wx.EXPAND|wx.ALL, 5 )
        
        self.m_staticline6 = wx.StaticLine( class_sizer.GetStaticBox(), wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.LI_HORIZONTAL )
        class_sizer.Add( self.m_staticline6, 0, wx.EXPAND | wx.ALL, 5 )
        
        self.tip = wx.StaticText( class_sizer.GetStaticBox(), wx.ID_ANY, _(u"Check the table Electrical Spacing in Calculator Tools while entering clearance value"), wx.DefaultPosition, wx.DefaultSize, 0 )
        self.tip.Wrap( 350 )
        
        class_sizer.Add(self.tip, 0, wx.EXPAND|wx.ALL, 5 )    
    
        main_sizer.Add( class_sizer, 1, wx.EXPAND, 5 )

        self.m_staticline4 = wx.StaticLine( self, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.LI_HORIZONTAL )
        main_sizer.Add( self.m_staticline4, 0, wx.EXPAND | wx.ALL, 5 )

        self.save_checkBox = wx.CheckBox( self, wx.ID_ANY, _(u"Save Settings?"), wx.DefaultPosition, wx.DefaultSize, wx.CHK_2STATE )
        main_sizer.Add( self.save_checkBox, 0, wx.ALL, 5 )

        self.m_staticline5 = wx.StaticLine( self, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.LI_HORIZONTAL )
        main_sizer.Add( self.m_staticline5, 0, wx.EXPAND | wx.ALL, 5 )

        sdbSizer = wx.StdDialogButtonSizer()
        self.sdbSizerOK = wx.Button( self, wx.ID_OK )
        sdbSizer.AddButton( self.sdbSizerOK )
        self.sdbSizerCancel = wx.Button( self, wx.ID_CANCEL )
        sdbSizer.AddButton( self.sdbSizerCancel )
        sdbSizer.Realize()

        main_sizer.Add( sdbSizer, 1, wx.EXPAND, 5 )

        # Bindings
        self.layer_choice.Bind(wx.EVT_COMBOBOX, self.OnLayerChange)
        self.class_choice.Bind(wx.EVT_COMBOBOX, self.OnComboBind)
        self.density_slider.Bind(wx.EVT_SLIDER, self.OnDensitySliderChange)
        self.density_spinCtrl.Bind(wx.EVT_SPINCTRL, self.OnDensitySpinChange)

        self.SetSizer( main_sizer )

        # Load if file exists
        self.LoadSettings()
        self.UpdateFields()
        self.UpdateLayerColor()
        self.Layout()

        self.Centre( wx.BOTH )

    def OnLayerChange(self, event):
        """Обработчик изменения выбранного слоя"""
        self.UpdateLayerColor()
        event.Skip()

    def UpdateLayerColor(self):
        """Обновляет цвет текста в зависимости от выбранного слоя"""
        selected_layer = self.layer_choice.GetString(self.layer_choice.GetSelection())
        
        # Get color for layer
        layer_color = self.layer_colors.get(selected_layer, self.default_layer_color)

        element_list = [self.layer_color]

        for element in element_list:
            element.SetForegroundColour(layer_color)
            element.Refresh()

    def OnComboBind(self, event):
        self.UpdateFields(is_settings=True)

    def UpdateFields(self, is_settings: bool = False):
        key = self.class_choice.GetSelection()+1
        values = self.board_class[f'Class{key}']

        min_clearance = values['Clearance']
        current_value = self.clearance_spinCtrlDouble.GetValue()
        self.clearance_spinCtrlDouble.SetRange(min_clearance, 3.00)
        
        if current_value < min_clearance:
            self.clearance_spinCtrlDouble.SetValue(min_clearance)
        
        if is_settings:
            self.clearance_spinCtrlDouble.SetValue(f"{values['Clearance']}")

    def OnDensitySliderChange(self, event):
        """Обработчик изменения ползунка плотности"""
        value = self.density_slider.GetValue()
        # Reload if changed
        if self.density_spinCtrl.GetValue() != value:
            self.density_spinCtrl.SetValue(value)
        event.Skip()
    
    def OnDensitySpinChange(self, event):
        """Обработчик изменения поля ввода плотности"""
        value = self.density_spinCtrl.GetValue()
        # Reload if changed
        if self.density_slider.GetValue() != value:
            self.density_slider.SetValue(value)
        event.Skip()

    def LoadSettings(self):
        """Загружает настройки из файла settings.json"""
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                self.ApplySettings(settings)
                print(f"Настройки загружены из {self.settings_file}")
            except Exception as e:
                print(f"Ошибка загрузки настроек: {e}")
        else:
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                settings = self.GetValues()
                json.dump(settings, f)
    
    def ApplySettings(self, settings: Dict):
        """Применяет настройки к элементам UI"""

        if 'layer_name' in settings:
            layer_index = self.layer_choice.FindString(settings['layer_name'])
            if layer_index != wx.NOT_FOUND:
                self.layer_choice.SetSelection(layer_index)

        if 'kind' in settings:
            shape_index = self.shape_choice.FindString(settings['kind'])
            if shape_index != wx.NOT_FOUND:
                self.shape_choice.SetSelection(shape_index)

        if 'size_mm' in settings:
            try:
                self.size_spinCtrlDouble.SetValue(float(settings['size_mm']))
            except:
                pass

        if 'density' in settings:
            try:
                self.density_slider.SetValue(int(settings['density']))
                self.density_spinCtrl.SetValue(int(settings['density']))
            except:
                pass
        
        if 'shift_x' in settings:
            try:
                self.offset_spinCtrlDouble.SetValue(float(settings['shift_x']))
            except:
                pass
        
        if 'shift_y' in settings:
            try:
                self.offset_y_spinCtrlDouble.SetValue(float(settings['shift_y']))
            except:
                pass

        if 'class' in settings:
            try:
                class_name = _('Board Class {i}').format(i=settings['class'])
                class_index = self.class_choice.FindString(class_name)
                if class_index != wx.NOT_FOUND:
                    self.class_choice.SetSelection(class_index)
            except:
                pass

        if 'element_clearance' in settings:
            try:
                self.clearance_spinCtrlDouble.SetValue(float(settings['element_clearance']))
            except:
                pass

        if 'object_clearance' in settings:
            try:
                self.clearance_spinCtrlDouble_2.SetValue(float(settings['object_clearance']))
            except:
                pass

    def GetValues(self):
        vals = {}
        layer_index = self.layer_choice.GetSelection()
        vals["layer_name"] = self.layer_choice.GetString(layer_index)
        vals["kind"] = self.shape_choice.GetString(self.shape_choice.GetSelection())
        vals["size_mm"] = max(0.6, min(2.0, float(self.size_spinCtrlDouble.GetValue())))
        vals["density"] = max(25, min(90, int(self.density_slider.GetValue())))
        try:
            vals["shift_x"] = float(self.offset_spinCtrlDouble.GetValue())
            vals["shift_y"] = float(self.offset_y_spinCtrlDouble.GetValue())
        except Exception:
            vals["shift_x"] = 0
            vals["shift_y"] = 0
        class_index = self.class_choice.GetSelection() + 1
        vals["class"] = class_index
        try:
            key = self.class_choice.GetSelection()+1
            values = self.board_class[f'Class{key}']
            clearance_value = float(self.clearance_spinCtrlDouble.GetValue())
            min_clearance = values['Clearance']
            if clearance_value < min_clearance:
                clearance_value = min_clearance
            vals["element_clearance"] = min(3.0, clearance_value)
        except Exception:
            vals["element_clearance"] = 0
        try:
            vals["object_clearance"] = min(3.0, float(self.clearance_spinCtrlDouble_2.GetValue()))
        except Exception:
            vals["object_clearance"] = 0
        return vals