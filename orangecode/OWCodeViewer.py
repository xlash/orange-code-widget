import sys
import numpy
from orangecode.CodeEditorTextEdit import CodeEditorTextEdit

import AnyQt.QtCore
from AnyQt.QtGui import (
    QColor, QBrush, QPalette, QFont, QTextDocument,
    QSyntaxHighlighter, QTextCharFormat, QTextCursor, QKeySequence,
    QTextCursor,QCursor
)
from AnyQt.QtWidgets import (
    QTextEdit,QPushButton
)

import Orange.data
from Orange.widgets.widget import OWWidget, Input, Output
from Orange.widgets import gui, settings
#from repr import repr

from Orange.data import Table,Variable,Domain,ContinuousVariable, DiscreteVariable, StringVariable
from numpy import float64
from numpy import nan

import os, math
import itertools
import re

class OWCodeViewer(OWWidget):
    name = "Code Viewer"
    description = "Display"
    icon = "icons/Code.svg"
    priority = 10
    keywords = ["source", "code", "display" ,"programming"]
    dataset_ix = 0
    dataset_len = -1

    show_configuration = False

    class Inputs:
        data = Input("Source Code", Orange.data.Table)

    #class Outputs:
    #    sample = Output("Sampled Data", Orange.data.Table)

    want_main_area = False

    settings_version = 1
    directory = settings.Setting("")

    def __init__(self):
        super().__init__()

        # GUI
        box = gui.widgetBox(self.controlArea, "Info")
        self.infoLabel = gui.widgetLabel(box, '')
        navPanelSection = gui.hBox(box)
        gui.rubber(navPanelSection)

        self.navPreviousButton = gui.button(
            navPanelSection, self, "<== Previous", callback=self.navigation_previous_file)
        self.navPreviousButton.setDisabled(True)
        self.navNextButton = gui.button(
            navPanelSection, self, "Next ==>", callback=self.navigation_next_file)
        self.navNextButton.setDisabled(True)

        self.code_editor = CodeEditorTextEdit()
        self.controlArea.layout().addWidget(self.code_editor)

        self.configMoreButton = gui.button(
            self.controlArea, self, "Src directory", callback=self.switch_configuration_visibility)

        self.configurationBox = gui.widgetBox(self.controlArea, "Configuration")
        gui.lineEdit(self.configurationBox, self, 'directory','Source Directory',callback=self.directory_changed)
        self.refresh_configuration_box()

        self.source_file = ""
        self.source_line = -1

    def switch_configuration_visibility(self,e):
        self.show_configuration = not(self.show_configuration)
        self.refresh_configuration_box()

    def refresh_configuration_box(self):
        if(self.show_configuration):
            self.configMoreButton.setText("Configuration <<")
            self.configurationBox.show()
        else:
            self.configMoreButton.setText("Configuration >>")
            self.configurationBox.hide()

    @Inputs.data
    def set_data(self, dataset):
        self.dataset = dataset
        if dataset is not None:
            self.dataset_len = len(dataset)
            self.dataset_ix = 0
            if self.dataset_len > 1:
                self.navNextButton.setDisabled(False)
            else:
                self.navNextButton.setDisabled(True)
            self.navPreviousButton.setDisabled(True)
            self.update_source_file()
        else:
            self.display_no_source_selected()

    def directory_changed(self):
        self.code_editor.setPlainText("")
        self.update_source_file()

    def process_line(self,line):
        """
        The extraction is based on values to avoid manual configuration.
        """
        all_attributes_index = []

        #Guessing based on values
        for var in itertools.chain(line.domain.attributes,line.domain.metas):
            i = line.domain.index(var.name)
            all_attributes_index.append(i)

        for attribute_index in all_attributes_index:
            try:
                line[attribute_index]
            except IndexError:
                print("More attributes than values on line {}".format(line))
                continue

            if(line[attribute_index] is not None):
                val = line[attribute_index].value
                if type(val) is str:
                    val_parts = val.split(":")
                    if(len(val_parts) == 2):
                        if(val_parts[1].isnumeric()):
                            self.source_file = val_parts[0]
                            self.source_line = int(val_parts[1])

    def update_source_file(self):
        # Update source file
        if(self.dataset_len < 1):
            self.display_no_source_selected()
        else:
            self.process_line(self.dataset[self.dataset_ix])
        # Display
        if(self.source_file != ""):
            #Update highlighter
            filename, extension = os.path.splitext(self.source_file)
            self.code_editor.set_highlighter(extension)

            try:
                with open(self.directory+"/"+self.source_file,'r') as file:
                    code = file.read()
                    self.code_editor.setPlainText(code)

                self.display_source_file()
            except IOError:
                _, err, _ = sys.exc_info()
                self.display_error(str(err))
        else:
            self.display_no_source_selected()
            return
        if(self.source_line != -1):
            #print(self.source_line)
            block = self.code_editor.document().findBlockByLineNumber(self.source_line-1)
            self.code_editor.setTextCursor(QTextCursor(block))
            self.code_editor.moveCursor(QTextCursor.EndOfBlock)

    def is_source_file(self,value):
        #print(value.__class__.__name__)
        if not(isinstance(value, str)):
            return False
        for extension in ['.java','.c','.cpp','.py','.js','.ruby','.jsp']:
            if(value.endswith(extension)):
                return True
        return False

    # Information display
    def display_no_source_selected(self):
        self.infoLabel.setText('No source file selected')

    def display_file_not_found(self):
        self.infoLabel.setText('Source file not found')

    def display_error(self,message):
        self.infoLabel.setText('An error has occured: '+message)

    def display_source_file(self):
        filename = self.source_file.split("/")[-1].split("\\")[-1]
        line = ("" if self.source_line == -1 else " ~ Line: <b>"+str(self.source_line)+"</b>")

        self.infoLabel.setText("Source file {}/{}: <b>{}</b> {} ".format(self.dataset_ix + 1,self.dataset_len,filename,line))

    def navigation_next_file(self):
        if self.dataset_ix == self.dataset_len -1:
            return
        self.dataset_ix += 1
        self.navPreviousButton.setDisabled(False)
        # Verify for end of dataset
        if self.dataset_ix == self.dataset_len -1:
            self.navNextButton.setDisabled(True)
        self.update_source_file()

    def navigation_previous_file(self):
        if self.dataset_ix == 0:
            return
        self.dataset_ix -= 1
        self.navNextButton.setDisabled(False)
        # Verify for beginning of dataset
        if self.dataset_ix == 0:
            self.navPreviousButton.setDisabled(True)
        self.update_source_file()
        
#For quick testing
if __name__ == "__main__":
    from AnyQt.QtWidgets import QApplication
    app = QApplication(sys.argv)
    ow = OWCodeViewer()
    ow.show()
    app.exec_()
    ow.saveSettings()
