import numpy as _np
from elements import elements
import os as _os

class pytransport(elements):
    """
    A module for converting a TRANSPORT file into gmad for use in BDSIM.
        
    To use:
    
    >>> self = pytransport.convert.pytransport(inputfile)
            
    Will output the lattice in the appropriate format.

    Parameters:
        
    particle: string
        The particle type, default = 'proton'.
        
    debug: boolean
        Output debug strings, default = False.
            
    distrType: string
        The distribution type of the beam, default = 'gauss'.
        Can only handle 'gauss' and 'gausstwiss'. If madx output is specified,
        the madx beam distribution is 'madx'.
            
    gmad: boolean
        Write the converted output into gmad format, default = True.
            
    gmadDir: string
        Output directory for gmad format, default = 'gmad'

    madx: boolean
        write the converted output into madx format, dafault = False.
            
    madxDir: string
        Output directory for madx format, default = 'madx'

    auto: boolean
        Automatically convert and output the file, default = True.

    keepName: boolean
        Keep original element name if present, default = False

    combineDrifts: boolean
        Combine consecutive drifts into a single drift, default = False
    
    outlog: boolean
        Output stream to a log file, default = True
    """
    def __init__(self, inputfile,
                 particle      = 'proton',
                 debug         = False,
                 distrType     = 'gauss',
                 gmad          = True,
                 gmadDir       = 'gmad',
                 madx          = False,
                 madxDir       = 'madx',
                 auto          = True,
                 dontSplit     = False,
                 keepName      = False,
                 combineDrifts = False,
                 outlog        = True):
        elements.__init__(inputfile, particle, debug, distrType, gmad, gmadDir, madx, madxDir,
                          auto, dontSplit, keepName, combineDrifts, outlog)

        self._load_file(inputfile)  # load file automatically
        if self._auto:
            self.transport2gmad()

    def Write(self):
        """
        Write the converted TRANSPORT file to disk.
        """
        if self._numberparts < 0:
            self._filename = self._file
        else:
            self._numberparts += 1
            self._filename = self._file+'_part'+_np.str(self._numberparts)
        self.create_beam()
        self.create_options()
        self.gmadmachine.AddSampler('all')
        self.madxmachine.AddSampler('all')
        if self._gmadoutput:
            if not self._dir_exists(self._gmadDir):
                _os.mkdir(self._gmadDir)
            _os.chdir(self._gmadDir)
            filename = self._filename + '.gmad'
            self.gmadmachine.Write(filename)
            _os.chdir('../')
        if self._madxoutput:
            if not self._dir_exists(self._madxDir):
                _os.mkdir(self._madxDir)
            _os.chdir(self._madxDir)
            filename = self._filename + '.madx'
            self.madxmachine.Write(filename)
            _os.chdir('../')

    def transport2gmad(self):
        """
        Function to convert TRANSPORT file on a line by line basis.
        """
        if not self._fileloaded:
            self._printout('No file loaded.')
            return
        self.ProcessAndBuild()
        self.Write()

    def _element_prepper(self, line, linenum, filetype='input'):
        """
        Function to extract the data and prepare it for processing by each element function.
        This has been written as the lattice lines from an input file and output file are different,
        so it just a way of correctly ordering the information.
        """
        linedict = {'elementnum'   : 0.0,
                    'name'         : '',
                    'length'       : 0.0,
                    'isZeroLength' : True}
        numElements = _np.str(len(self._elementReg.elements))
        typeNum = self._getTypeNum(line)
        linedict['elementnum'] = typeNum
        
        if typeNum == 15.0:
            label = self._get_label(line)
            if filetype == 'output':
                linedict['label'] = line[2].strip('"')
            if filetype == 'input':
                linedict['label'] = label
            linedict['number'] = line[1]
            self._debug_printout("\tEntry is a Unit Control, adding to the element registry as element " + numElements + ".")
        
        if typeNum == 20.0:
            angle = 0  # Default
            if len(line) == 2:  # i.e has a label
                endofline = self._endofline(line[1])
                angle = line[1][:endofline]
            else:
                for index in line[1:]:
                    try:
                        angle = _np.float(index)
                        break
                    except ValueError:
                        pass
            linedict['angle'] = angle
            self._debug_printout("\tEntry is a coordinate rotation, adding to the element registry as element " +
                               numElements + ".")

        if typeNum == 1.0:
            linedict['name'] = self._get_label(line)
            linedict['isAddition'] = False
            if self._is_addition(line, filetype):
                linedict['isAddition'] = True
            # line = self._remove_label(line)
            if len(line) < 8:
                raise IndexError("Incorrect number of beam parameters.")
            n = 1
            if filetype == 'input':
                n = 0
            elif filetype == 'output':
                n = 1
            
            # Find momentum
            # endofline = self._endofline(line[7+n])
            # if endofline != -1:
            #     linedict['momentum'] = line[7+n][:endofline]
            # else:
            linedict['momentum'] = line[7+n]
            linedict['Sigmax'] = line[1+n]
            linedict['Sigmay'] = line[3+n]
            linedict['Sigmaxp'] = line[2+n]
            linedict['Sigmayp'] = line[4+n]
            linedict['SigmaT'] = line[5+n]
            linedict['SigmaE'] = line[6+n]
            self._debug_printout("\tEntry is a Beam definition or r.m.s addition, adding to the element registry as element " + numElements + ".")

        if typeNum == 2.0:
            linedict['name'] = self._get_label(line)
            linedict['data'] = self._get_elementdata(line)
            self._debug_printout("\tEntry is a poleface rotation, adding to the element registry as element " + numElements + ".")
        
        if typeNum == 3.0:
            linedict['name'] = self._get_label(line)
            data = self._get_elementdata(line)
            linedict['length'] = data[0]
            linedict['isZeroLength'] = False
            self._debug_printout("\tEntry is a drift tube, adding to the element registry as element " + numElements + ".")
            
        if typeNum == 4.0:
            linedict['name'] = self._get_label(line)
            linedict['linenum'] = linenum
            data = self._get_elementdata(line)
            linedict['data'] = data
            linedict['length'] = data[0]
            linedict['isZeroLength'] = False
            e1, e2 = self._facerotation(line, linenum)
            linedict['e1'] = e1
            linedict['e2'] = e2
            self._debug_printout("\tEntry is a dipole, adding to the element registry as element " + numElements + ".")

        if typeNum == 5.0:
            linedict['name'] = self._get_label(line)
            data = self._get_elementdata(line)
            linedict['data'] = data
            linedict['length'] = data[0]
            linedict['isZeroLength'] = False
            self._debug_printout("\tEntry is a quadrupole, adding to the element registry as element " + numElements + ".")

        if typeNum == 6.0:
            # element is a collimator or transform update
            # transform update is later ignored so only update linedict as if collimator

            physicalElements = [1.0, 3.0, 4.0, 5.0, 11.0, 18.0, 19.0]

            # Only iterate if not the last element
            if linenum == len(self.data):
                pass
            else:
                # Since collimators have zero length in TRANSPORT, chosen to use length of next drift instead if
                # present. Check all remaining elements for the next drift, following element(s) may be non-physical
                # element which can be ignored as it shouldnt affect the beamline. Ignore beam definition too in
                # the case where machine splitting is not permitted.
                for nextline in self.data[linenum+1:]:
                    nextTypeNum = self._getTypeNum(nextline)
                    if nextTypeNum == 3.0:
                        nextData = self._get_elementdata(nextline)
                        linedict['length'] = nextData[0]
                        linedict['isZeroLength'] = False
                        linedict['name'] = self._get_label(line)
                        data = self._get_elementdata(line)
                        linedict['data'] = data
                        break
                    # stop if physical element or beam redef if splitting permitted
                    elif nextTypeNum in physicalElements:
                        if (nextTypeNum == 1.0) and self._dontSplit:
                            pass
                        elif (nextTypeNum == 6.0) and self._typeCode6IsTransUpdate:
                            pass
                        else:
                            break
                    # ignore non-physical element
                    else:
                        pass
                
            # Can be either transform update or collimator, a 16. 14 entry changes the definition but is only
            # processed after ALL elements are added to the registry.
            self._debug_printout("\tEntry is either a Transform update or collimator, adding to the element registry as element " + numElements + ".")

        if typeNum == 9.0:
            self._debug_printout("\tEntry is a repetition control, adding to the element registry as element " + numElements + ".")

        if typeNum == 11.0:
            linedict['name'] = self._get_label(line)
            data = self._get_elementdata(line)
            linedict['data'] = data
            linedict['length'] = data[0]
            linedict['voltage'] = data[1]
            linedict['isZeroLength'] = False
            if len(data) == 4:  # Older case for single element
                linedict['phase_lag'] = data[2]
                linedict['wavel'] = data[3]
            self._debug_printout("\tEntry is an acceleration element, adding to the element registry as element " + numElements + ".")

        if typeNum == 12.0:
            linedict['data'] = self._get_elementdata(line)
            linedict['name'] = self._get_label(line)

            prevline = self.data[linenum-1]  # .split(' ')
            linedict['prevlinenum'] = _np.float(prevline[0])
            linedict['isAddition'] = False
            if self._is_addition(line):
                linedict['isAddition'] = True
            self._debug_printout("\tEntry is a beam rotation, adding to the element registry as element " + numElements + ".")
                
        if typeNum == 13.0:
            linedict['data'] = self._get_elementdata(line)
            self._debug_printout("\tEntry is a Input/Output control, adding to the element registry as element " + numElements + ".")
        
        if typeNum == 16.0:
            linedict['data'] = self._get_elementdata(line)
            self._debug_printout("\tEntry is a special input, adding to the element registry as element " + numElements + ".")

        if typeNum == 18.0:
            linedict['name'] = self._get_label(line)
            data = self._get_elementdata(line)
            linedict['data'] = data
            linedict['length'] = data[0]
            linedict['isZeroLength'] = False
            self._debug_printout("\tEntry is a sextupole, adding to the element registry as element " + numElements + ".")
        
        if typeNum == 19.0:
            linedict['name'] = self._get_label(line)
            data = self._get_elementdata(line)
            linedict['data'] = data
            linedict['length'] = data[0]
            linedict['isZeroLength'] = False
            self._debug_printout("\tEntry is a solenoid, adding to the element registry as element " + numElements + ".")

        if typeNum == 22.0:
            self._debug_printout("\tEntry is a space charge element, adding to the element registry as element " + numElements + ".")

        if typeNum == 23.0:
            self._debug_printout("\tEntry is a buncher, adding to the element registry as element " + numElements + ".")

        rawline = self.filedata[linenum]
        self._elementReg.AddToRegistry(linedict, rawline)

    def ProcessAndBuild(self):
        """
        Function that loops over the lattice, adds the elements to the element registry,
        and updates any elements that have fitted parameters.
        It then converts the registry elements into pybdsim format and add to the pybdsim builder.
        """
        self._debug_printout('Converting registry elements to pybdsim compatible format and adding to machine builder.')

        for linenum, line in enumerate(self.data):
            self._debug_printout('Processing tokenised line '+_np.str(linenum)+' :')
            self._debug_printout('\t' + str(line))
            self._debug_printout('Original :')
            self._debug_printout('\t' + self.filedata[linenum])

            # Checks if the SENTINEL line is found. SENTINEL relates to TRANSPORT fitting routine and is only written
            # after the lattice definition, so there's no point reading lines beyond it.
            if self._is_sentinel(line):
                self._debug_printout('Sentinel Found.')
                break
            # Test for positive element, negative ones ignored in TRANSPORT so ignored here too.
            try:
                typeNum = self._getTypeNum(line)
                if typeNum > 0:
                    if self.data[0][0] == 'OUTPUT':
                        self._element_prepper(line, linenum, 'output')
                        self.UpdateElementsFromFits()
                    else:
                        line = self._remove_illegals(line)
                        self._element_prepper(line, linenum, 'input')
                else:
                    self._debug_printout('\tType code is 0 or negative, ignoring line.')
            except ValueError:
                errorline = '\tCannot process line '+_np.str(linenum) + ', '
                if line[0][0] == '(' or line[0][0] == '/':
                    errorline += 'line is a comment.'
                elif line[0][0] == 'S':  # S used as first character in SENTINEL command.
                    errorline = 'line is for TRANSPORT fitting routine.'
                elif line[0] == '\n':
                    errorline = 'line is blank.'
                else:
                    errorline = 'reason unknown.'
                self._debug_printout(errorline)

        skipNextDrift = False  # used for collimators
        lastElementWasADrift = True  # default value
        if self._combineDrifts:
            lastElementWasADrift = False
        for linenum, linedict in enumerate(self._elementReg.elements):
            if self._debug:
                debugstring = 'Converting element number ' + _np.str(linenum) + ':'
                self._printout(debugstring)
                convertline = '\t'
                for keynum, key in enumerate(linedict.keys()):
                    if keynum != 0:
                        convertline += ', '
                    if key == 'data':
                        convertline += 'element data:'
                        for ele in linedict[key]:
                            convertline += ('\t'+_np.str(ele))
                    else:
                        convertline += (key + ': '+_np.str(linedict[key]))
                    if keynum == len(linedict.keys()):
                        convertline += '.'
                self._printout(convertline)

            if self._combineDrifts:
                if lastElementWasADrift and linedict['elementnum'] != 3.0 and linedict['elementnum'] < 20.0:
                    # write possibly combined drift
                    self._debug_printout('\n\tConvert delayed drift(s)')
                    self.drift(linedictDrift)
                    lastElementWasADrift = False
                    self._debug_printout('\n\tNow convert element number' + _np.str(linenum))

            if linedict['elementnum'] == 15.0:
                self.unit_change(linedict)
            if linedict['elementnum'] == 20.0:
                self.change_bend(linedict)
            if linedict['elementnum'] == 1.0:  # Add beam on first definition
                if not self._beamdefined:
                    self.define_beam(linedict)
                elif not self._dontSplit:  # Only update beyond first definition if splitting is permitted
                    self.define_beam(linedict)
            if linedict['elementnum'] == 3.0:
                if skipNextDrift:
                    skipNextDrift = False
                    continue
                if self._combineDrifts:
                    self._debug_printout('\tDelay drift')
                    if lastElementWasADrift:
                        linedictDrift['length'] += linedict['length']  # update linedictDrift
                        if not linedictDrift['name']:
                            linedictDrift['name'] = linedict['name']  # keep first non-empty name
                    else:
                        linedictDrift = linedict   # new linedictDrift
                        lastElementWasADrift = True
                else:
                    self.drift(linedict)
            if linedict['elementnum'] == 4.0:
                self.dipole(linedict)
            if linedict['elementnum'] == 5.0:
                self.quadrupole(linedict)
            if linedict['elementnum'] == 6.0:
                if not self._typeCode6IsTransUpdate:
                    self.collimator(linedict)
                    # Length gotten from next drift
                    if linedict['length'] > 0.0:
                        skipNextDrift = True
                else:
                    self._transformUpdate(linedict)
            if linedict['elementnum'] == 12.0:
                self.correction(linedict)
            if linedict['elementnum'] == 11.0:
                self.acceleration(linedict)
            if linedict['elementnum'] == 13.0:
                self.printline(linedict)
            if linedict['elementnum'] == 16.0:
                self.special_input(linedict)
            if linedict['elementnum'] == 18.0:
                self.sextupole(linedict)
            if linedict['elementnum'] == 19.0:
                self.solenoid(linedict)

            # 9.  : 'Repetition' - for nesting elements
            if linedict['elementnum'] == 9.0:
                self._debug_printout('\tWARNING Repetition Element not implemented in converter!')
            if linedict['elementnum'] == 2.0:
                errorline = '\tLine is a poleface rotation which is handled by the previous or next dipole element.'
                self._debug_printout(errorline)
            
            self._debug_printout('\n')

        # OTHER TYPES WHICH CAN BE IGNORED:
        # 6.0.X : Update RX matrix used in TRANSPORT
        # 7.  : 'Shift beam centroid'
        # 8.  : Magnet alignment tolerances
        # 10. : Fitting constraint
        # 14. : Arbitrary transformation of TRANSPORT matrix
        # 22. : Space charge element
        # 23. : RF Cavity (Buncher), changes bunch energy spread

        # Write also last drift
        if self._combineDrifts:
            if lastElementWasADrift:
                self._debug_printout('\tConvert delayed drift(s)')
                self.drift(linedictDrift)
       
    def create_beam(self):
        """
        Function to prepare the beam for writing.
        """
        # convert energy to GeV (madx only handles GeV)
        energy_in_gev = self.beamprops.tot_energy * self.scale[self.units['p_egain'][0]] / 1e9
        self.beamprops.tot_energy = energy_in_gev
        
        self.madxbeam.SetParticleType(self._particle)
        self.madxbeam.SetEnergy(energy=self.beamprops.tot_energy, unitsstring='GeV')

        self.gmadbeam.SetParticleType(self._particle)
        self.gmadbeam.SetEnergy(energy=self.beamprops.tot_energy, unitsstring='GeV')

        # set gmad parameters depending on distribution
        if self.beamprops.distrType == 'gausstwiss':
            self.gmadbeam.SetDistributionType(self.beamprops.distrType)
            self.gmadbeam.SetBetaX(self.beamprops.betx)
            self.gmadbeam.SetBetaY(self.beamprops.bety)
            self.gmadbeam.SetAlphaX(self.beamprops.alfx)
            self.gmadbeam.SetAlphaY(self.beamprops.alfy)
            self.gmadbeam.SetEmittanceX(self.beamprops.emitx, unitsstring='mm')
            self.gmadbeam.SetEmittanceY(self.beamprops.emity, unitsstring='mm')
            self.gmadbeam.SetSigmaE(self.beamprops.SigmaE)
            self.gmadbeam.SetSigmaT(self.beamprops.SigmaT)

        else:
            self.gmadbeam.SetDistributionType(self.beamprops.distrType)
            self.gmadbeam.SetSigmaX(self.beamprops.SigmaX, unitsstring=self.units['x'])
            self.gmadbeam.SetSigmaY(self.beamprops.SigmaY, unitsstring=self.units['y'])
            self.gmadbeam.SetSigmaXP(self.beamprops.SigmaXP, unitsstring=self.units['xp'])
            self.gmadbeam.SetSigmaYP(self.beamprops.SigmaYP, unitsstring=self.units['yp'])
            self.gmadbeam.SetSigmaE(self.beamprops.SigmaE)
            self.gmadbeam.SetSigmaT(self.beamprops.SigmaT)
            
            # calculate betas and emittances regardless for madx beam
            try:
                self.beamprops.betx = self.beamprops.SigmaX / self.beamprops.SigmaXP
            except ZeroDivisionError:
                self.beamprops.betx = 0
            try:
                self.beamprops.bety = self.beamprops.SigmaY / self.beamprops.SigmaYP
            except ZeroDivisionError:
                self.beamprops.bety = 0
            self.beamprops.emitx = self.beamprops.SigmaX * self.beamprops.SigmaXP / 1000.0
            self.beamprops.emity = self.beamprops.SigmaY * self.beamprops.SigmaYP / 1000.0
        
        # set madx beam
        self.madxbeam.SetDistributionType('madx')
        self.madxbeam.SetBetaX(self.beamprops.betx)
        self.madxbeam.SetBetaY(self.beamprops.bety)
        self.madxbeam.SetAlphaX(self.beamprops.alfx)
        self.madxbeam.SetAlphaY(self.beamprops.alfy)
        self.madxbeam.SetEmittanceX(self.beamprops.emitx/1000)
        self.madxbeam.SetEmittanceY(self.beamprops.emity/1000)
        self.madxbeam.SetSigmaE(self.beamprops.SigmaE)
        self.madxbeam.SetSigmaT(self.beamprops.SigmaT)
        
        # set beam offsets in gmad if non zero
        if self.beamprops.X0 != 0:
            self.gmadbeam.SetX0(self.beamprops.X0, unitsstring=self.units['x'])
        if self.beamprops.Y0 != 0:
            self.gmadbeam.SetY0(self.beamprops.Y0, unitsstring=self.units['y'])
        if self.beamprops.Z0 != 0:
            self.gmadbeam.SetZ0(self.beamprops.Z0, unitsstring=self.units['z'])

        self._print_beam_debug()

        self.gmadmachine.AddBeam(self.gmadbeam)
        self.madxmachine.AddBeam(self.madxbeam)

    def create_options(self):
        """
        Function to set the Options for the BDSIM machine.
        """
        self.options.SetPhysicsList(physicslist='em')
        self.options.SetBeamPipeRadius(beampiperadius=self.machineprops.beampiperadius, unitsstring=self.units['pipe_rad'])
        self.options.SetOuterDiameter(outerdiameter=0.5, unitsstring='m')
        self.options.SetTunnelRadius(tunnelradius=1, unitsstring='m')
        self.options.SetBeamPipeThickness(bpt=5, unitsstring='mm')
        self.options.SetSamplerDiameter(radius=1, unitsstring='m')
        self.options.SetStopTracks(stop=True)
        self.options.SetIncludeFringeFields(on=True)
        
        self.gmadmachine.AddOptions(self.options)
        self.madxmachine.AddOptions(self.options)  # redundant

    def UpdateElementsFromFits(self):
        # Functions that update the elements in the element registry.
        # For debugging purposes, they return dictionaries of the element type,
        # length change details, and which parameters were updated and the values in a list which
        # follows the pattern of [parameter name (e.g. 'field'),oldvalue,newvalue]
        
        # Length update common to nearly all elements, seperate function to prevent duplication
        def _updateLength(index, fitindex, element):
            oldlength = self._elementReg.elements[index]['length']
            lengthDiff = self._elementReg.elements[index]['length'] - element['length']
            self._elementReg.elements[index]['length'] = element['length']  # Update length
            self._elementReg.length[index:] += lengthDiff                   # Update running length of subsequent elements.
            self._elementReg._totalLength += lengthDiff                     # Update total length
            lendict = {'old': _np.round(oldlength, 5),
                       'new': _np.round(element['length'], 5)}
            return lendict

        def _updateDrift(index, fitindex, element):
            eledict = {'updated': False,
                       'element': 'Drift',
                       'params': []}

            # Only length can be varied
            if self._elementReg.elements[index]['length'] != element['length']:
                lendict = _updateLength(index, fitindex, element)
                eledict['updated'] = True
                eledict['length'] = lendict
            return eledict

        def _updateQuad(index, fitindex, element):
            eledict = {'updated': False,
                       'element': 'Quadrupole',
                       'params': []}
            
            if self._elementReg.elements[index]['data'][1] != element['data'][1]:  # Field
                oldvalue = self._elementReg.elements[index]['data'][1]
                self._elementReg.elements[index]['data'][1] = element['data'][1]
                eledict['updated'] = True
                data = ['field', oldvalue, element['data'][1]]
                eledict['params'].append(data)

            if self._elementReg.elements[index]['length'] != element['length']:
                self._elementReg.elements[index]['data'][0] = element['data'][0]  # Length in data
                lendict = _updateLength(index, fitindex, element)
                eledict['updated'] = True
                eledict['length'] = lendict
            return eledict

        def _updateDipole(index, fitindex, element):
            eledict = {'updated': False,
                       'element': 'Dipole',
                       'params': []}
            
            # TODO: Need code in here to handle variation in poleface rotation. Not urgent for now.
            if self._elementReg.elements[index]['data'][1] != element['data'][1]:  # Field
                oldvalue = self._elementReg.elements[index]['data'][1]
                self._elementReg.elements[index]['data'][1] = element['data'][1]
                eledict['updated'] = True
                if self.machineprops.benddef:  # Transport can switch dipole input definition
                    par = 'field'
                else:
                    par = 'angle'
                data = [par, oldvalue, element['data'][3]]
                eledict['params'].append(data)
            if self._elementReg.elements[index]['length'] != element['length']:
                self._elementReg.elements[index]['data'][0] = element['data'][0]  # Length in data
                lendict = _updateLength(index, fitindex, element)
                eledict['updated'] = True
                eledict['length'] = lendict
            return eledict

        for index, name in enumerate(self._fitReg._uniquenames):
            fitstart = self._fitReg.GetElementStartSPosition(name)
            elestart = self._elementReg.GetElementStartSPosition(name)
            fitindex = self._fitReg.GetElementIndex(name)
            eleindex = self._elementReg.GetElementIndex(name)
            for fitnum, fit in enumerate(fitstart):
                for elenum, ele in enumerate(elestart):
                    if (_np.round(ele, 5) == _np.round(fit, 5)) and \
                            (not self._elementReg.elements[eleindex[elenum]]['isZeroLength']):
                        fitelement = self._fitReg.elements[fitindex[fitnum]]
                        if fitelement['elementnum'] == 3:
                            eledict = _updateDrift(eleindex[elenum], fitindex[fitnum], fitelement)
                        elif fitelement['elementnum'] == 4:
                            eledict = _updateDipole(eleindex[elenum], fitindex[fitnum], fitelement)
                        elif fitelement['elementnum'] == 5:
                            eledict = _updateQuad(eleindex[elenum], fitindex[fitnum], fitelement)
            
                        if eledict['updated']:
                            self._debug_printout("\tElement " + _np.str(eleindex[elenum]) + " was updated from fitting.")
                            self._debug_printout("\tOptics Output line:")
                            self._debug_printout("\t\t'" + self._fitReg.lines[fitindex[fitnum]] + "'")
                            if eledict.has_key('length'):
                                lenline = "\t"+eledict['element']+" length updated to "
                                lenline += _np.str(eledict['length']['new'])
                                lenline += " (from " + _np.str(eledict['length']['old']) + ")."
                                self._debug_printout(lenline)
                            for param in eledict['params']:
                                parline = "\t" + eledict['element'] + " " + param[0]
                                parline += " updated to " + _np.str(param[2]) + " (from " + _np.str(param[1]) + ")."
                                self._debug_printout(parline)
                            self._debug_printout("\n")
                
                        break
