# -*- coding: utf-8 -*-

from rules_symbol.rule import *
import re


class Rule(KLCRule):
    """Power flag symbols"""

    def __init__(self, component):
        super().__init__(component)

        self.makePinINVISIBLE = False
        self.makePinPowerInput = False
        self.fixTooManyPins = False
        self.fixPinSignalName = False
        self.fixNoFootprint = False
        self.fixWrongRef = False

    def check(self):
        fail = False

        if self.component.is_power_symbol():
            if (len(self.component.pins) != 1):
                self.error("Power-flag symbols have exactly one pin")
                fail = True
                self.fixTooManyPins = True
            else:
                if (self.component.pins[0].etype != 'power_in'):
                    self.error("The pin in power-flag symbols has to be of a POWER-INPUT")
                    fail = True
                    self.makePinPowerInput = True
                if (self.component.pins[0].is_hidden != True):
                    self.error("The pin in power-flag symbols has to be INVISIBLE")
                    fail = True
                    self.makePinINVISIBLE = True
                if ((self.component.pins[0].name != self.component.name) and ('~'+self.component.pins[0].name != self.component.name)):
                    self.error("The pin name ("+self.component.pins[0].name+") in power-flag symbols has to be the same as the component name ("+self.component.name+")")
                    fail = True
                    self.fixPinSignalName = True
                # footprint field must be empty
                fp_prop = self.component.get_property("Footprint")
                if fp_prop and fp_prop.value != '':
                    self.error("Power symbols have no footprint association (footprint is set to '"+fp_prop.value+"')")
                    fail = True
                    self.fixNoFootprint = True
                ref_prop = self.component.get_property("Reference")
                if not ref_prop or ref_prop.value != '#PWR':
                    self.error("Power symbols have Reference set to '#PWR' ")
                    fail = True
                    self.fixWrongRef = True
                # FPFilters must be empty
                if len(self.component.get_fp_filters()) > 0:
                    self.error("Graphical symbols have no footprint filters")
                    fail = True
                    self.fixNoFootprint = True

        return fail

    def fix(self):
        """
        Proceeds the fixing of the rule, if possible.
        """
        if self.fixTooManyPins:
            self.info("FIX for too many pins in power-symbol not supported")
        if self.makePinPowerInput:
            self.info("FIX: switching pin-type to power-input")
            self.component.pins[0].etype = 'power_in'
        if self.makePinINVISIBLE:
            self.info("FIX: making pin invisible")
            self.component.pins[0].is_hidden = True
        if self.fixPinSignalName:
            newname = self.component.name
            if self.component.name.startswith('~'):
                newname = self.component.name[1:len(self.component.name)]
            self.info("FIX: change pin name to '"+newname+"'")
            self.component.pins[0].name = newname
        if self.fixNoFootprint:
            self.info("FIX empty footprint association and FPFilters")
            self.component.get_property("Footprint").value = ""
            self.component.get_property("ki_fp_filters").value = ""
