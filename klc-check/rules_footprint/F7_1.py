# -*- coding: utf-8 -*-

from rules_footprint.rule import *

class Rule(KLCRule):
    """For through-hole devices, placement type must be set to "Through Hole" """

    def __init__(self, component, args):
        super().__init__(component, args)

        self.pth_count = 0
        self.smd_count = 0

    def check(self):
        """
        Proceeds the checking of the rule.
        The following variables will be accessible after checking:
            * pads_bounds
            * pads_distance
            * right_anchor
        """
        module = self.module

        self.pth_count = len(module.filterPads('thru_hole'))
        self.smd_count = len(module.filterPads('smd'))

        error = False

        if self.pth_count > 0 and module.attribute != 'through_hole':
            if module.attribute == 'virtual':
                self.warning("Footprint placement type set to 'virtual' - ensure this is correct!")
            # Only THT pads
            elif self.smd_count == 0:
                self.error("Through Hole attribute not set")
                self.errorExtra("For THT footprints, 'Placement type' must be set to 'Through hole'")
                error = True
            # A mix of THT and SMD pads - probably a SMD footprint

        return error


    def fix(self):
        """
        Proceeds the fixing of the rule, if possible.
        """
        module = self.module
        if self.check():
            self.info("Setting placement type to 'Through hole'")
            module.attribute = 'through_hole'
