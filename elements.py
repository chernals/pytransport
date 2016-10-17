import numpy as _np
from scipy import constants as _con
from pymadx import Builder as _mdBuilder
from pybdsim import Builder as _pyBuilder
import string as _string
from _General import functions
    
class elements(functions):
    def define_beam(self,linedict):
        if linedict['isAddition']:
            if self._debug:
                self._printout('\tIgnoring beam rms addition.')
            return
        if self._beamdefined:
            self._numberparts += 1
            self.write()
            self._printout('Writing...')
            del self.gmadmachine
            del self.madxmachine
            self.gmadmachine = _pyBuilder.Machine()
            self.madxmachine = _mdBuilder.Machine()
            self._correctedbeamdef = False
            
            self._printout('\tBeam redefinition found. Writing previous section to file.')
            self._printout('\tSplitting into multiple machines.')
        
        momentum = linedict['momentum']

        self._beamdefined = True
       
        #Convert momentum to energy and set distribution params.
        self._calculate_energy(momentum)
        self.beamprops.SigmaX  = _np.float(linedict['Sigmax'])
        self.beamprops.SigmaY  = _np.float(linedict['Sigmay'])
        self.beamprops.SigmaXP = _np.float(linedict['Sigmaxp'])
        self.beamprops.SigmaYP = _np.float(linedict['Sigmayp'])
        self.beamprops.SigmaE  = _np.float(linedict['SigmaE']) * 0.01 * (self.beamprops.beta**2) ## Convert from percentage mom spread to absolute espread
        self.beamprops.SigmaT  = self._bunch_length_convert(_np.float(linedict['SigmaT'])) ## Get bunch length in seconds.

        
        #Calculate Initial Twiss params
        try:
            self.beamprops.betx = self.beamprops.SigmaX / self.beamprops.SigmaXP
        except ZeroDivisionError:
            self.beamprops.betx= 0
        try:
            self.beamprops.bety = self.beamprops.SigmaY / self.beamprops.SigmaYP
        except ZeroDivisionError:
            self.beamprops.bety= 0
        self.beamprops.emitx = self.beamprops.SigmaX * self.beamprops.SigmaXP / 1000.0
        self.beamprops.emity = self.beamprops.SigmaY * self.beamprops.SigmaYP / 1000.0

        if self._debug:
            self._printout('\t Beam definition :')
            self._printout('\t distrType = ' + self.beamprops.distrType)
            self._printout('\t energy = ' + _np.str(self.beamprops.tot_energy)+ ' ' +self.units['p_egain'])
            self._printout('\t SigmaX = ' + _np.str(self.beamprops.SigmaX)  + ' ' +self.units['x'])
            self._printout('\t SigmaXP = '+ _np.str(self.beamprops.SigmaXP) + ' ' +self.units['xp'])
            self._printout('\t SigmaY = ' + _np.str(self.beamprops.SigmaY)  + ' ' +self.units['y'])
            self._printout('\t SigmaYP = '+ _np.str(self.beamprops.SigmaYP) + ' ' +self.units['yp'])
            self._printout('\t SigmaE = ' + _np.str(self.beamprops.SigmaE))
            self._printout('\t SigmaT = ' + _np.str(self.beamprops.SigmaT))
            self._printout('\t (Final brho = '  + _np.str(_np.round(self.beamprops.brho,2))+' Tm)')
            self._printout('\t Twiss Params:')
            self._printout('\t BetaX = ' +_np.str(self.beamprops.betx) + ' ' + self.units['beta_func'])
            self._printout('\t BetaY = ' +_np.str(self.beamprops.bety) + ' ' + self.units['beta_func'])
            self._printout('\t AlphaX = '+_np.str(self.beamprops.alfx))
            self._printout('\t AlphaY = '+_np.str(self.beamprops.alfy))
            self._printout('\t Emittx = '+_np.str(self.beamprops.emitx) + ' ' + self.units['emittance'])
            self._printout('\t EmittY = '+_np.str(self.beamprops.emity) + ' ' + self.units['emittance'])
        
    
    def drift(self,linedict):
        driftlen = linedict['driftlen']
        if _np.float(driftlen) <= 0:
            if self._debug:
                self._printout('\tZero or negative length element, ignoring.')
            return
    
        if self.units['element_length'] != 'm':
            length_in_metres = _np.float(driftlen) * self.scale[self.units['element_length'][0]]  #Convert to metres.
        else:
            length_in_metres = _np.float(driftlen)

        self.machineprops.drifts += 1
        elementid = 'DR'+_np.str(self.machineprops.drifts)

        self.gmadmachine.AddDrift(name=elementid,length=length_in_metres)
        self.madxmachine.AddDrift(name=elementid,length=length_in_metres)
        
        if self._debug:
            self._printout('\tConverted to:')
            debugstring = 'Drift '+elementid+', length '+_np.str(length_in_metres)+' m'
            self._printout('\t'+debugstring)

        
    def dipole(self,linedict):
        linenum = linedict['linenum']
        dipoledata = linedict['data']
        length = dipoledata[0]          # First two non-blanks must be the entries in a specific order.
        
        ## Get poleface rotation
        #e1 = self._facerotation(line,linenum-1) * (_np.pi / 180.0) * self.machineprops.bending  ## Entrance pole face rotation.
        #e2 = self._facerotation(line,linenum+1) * (_np.pi / 180.0) * self.machineprops.bending  ## Exit pole face rotation.
        e1 = linedict['e1'] * ((_np.pi / 180.0)*self.machineprops.bending)
        e2 = linedict['e2'] * ((_np.pi / 180.0)*self.machineprops.bending)
        
        if self._debug:
            if e1 != 0:
                self._printout('\tPreceding element ('+_np.str(linenum-1)+') provides an entrance poleface rotation of '+_np.str(_np.round(e1,4))+' rad.')
            if e2 != 0:
                self._printout('\tFollowing element ('+_np.str(linenum+1)+') provides an exit poleface rotation of '+_np.str(_np.round(e2,4))+' rad.')
        
        ##Calculate bending angle
        if self.machineprops.benddef:
            bfield = dipoledata[1]
            field_in_Gauss = bfield * self.scale[self.units['magnetic_fields'][0]]  # Scale to Gauss
            field_in_Tesla = field_in_Gauss * 1e-4                                  # Convert to Tesla
            if field_in_Tesla == 0:
                angle = 0                                                           # zero field = zero angle
            else:
                rho = self.beamprops.brho / (_np.float(field_in_Tesla))             # Calculate bending radius.
                angle = (_np.float(length) / rho) * self.machineprops.bending       # for direction of bend
            if self._debug:
                self._printout('\tbfield = '+_np.str(field_in_Gauss)+' kG')
                self._printout('\tbfield = '+_np.str(field_in_Tesla)+' T')
                self._printout('\tCorresponds to angle of '+_np.str(_np.round(angle,4)) + ' rad.')
        elif not self.machineprops.benddef:
            angle_in_deg = dipoledata[1]
            angle = angle_in_deg * (_np.pi/180.) * self.machineprops.bending
        
        ##Convert element length
        if self.units['element_length'] != 'm':
            length_in_metres = length * self.scale[self.units['element_length'][0]]
        else:
            length_in_metres = length
        
        self.machineprops.dipoles += 1
        elementid = 'BM'+_np.str(self.machineprops.dipoles)
        
        ##Check for non zero pole face rotation
        if (e1 != 0) and (e2 != 0):
            self.gmadmachine.AddDipole(name=elementid,category='sbend',length=length_in_metres,angle=_np.round(angle,4),e1=_np.round(e1,4),e2=_np.round(e2,4))
            self.madxmachine.AddDipole(name=elementid,category='sbend',length=length_in_metres,angle=_np.round(angle,4),e1=_np.round(e1,4),e2=_np.round(e2,4))
        elif (e1 != 0) and (e2 == 0):
            self.gmadmachine.AddDipole(name=elementid,category='sbend',length=length_in_metres,angle=_np.round(angle,4),e1=_np.round(e1,4))
            self.madxmachine.AddDipole(name=elementid,category='sbend',length=length_in_metres,angle=_np.round(angle,4),e1=_np.round(e1,4))
        elif (e1 == 0) and (e2 != 0):
            self.gmadmachine.AddDipole(name=elementid,category='sbend',length=length_in_metres,angle=_np.round(angle,4),e2=_np.round(e2,4))
            self.madxmachine.AddDipole(name=elementid,category='sbend',length=length_in_metres,angle=_np.round(angle,4),e2=_np.round(e2,4))
        else:
            self.gmadmachine.AddDipole(name=elementid,category='sbend',length=length_in_metres,angle=_np.round(angle,4))
            self.madxmachine.AddDipole(name=elementid,category='sbend',length=length_in_metres,angle=_np.round(angle,4))

        ## Debug output
        if self._debug:
            if (e1 != 0) and (e2 != 0):
                polefacestr = ', e1= '+_np.str(_np.round(e1,4))+' rad, e2= '+_np.str(_np.round(e2,4))+' rad'
            elif (e1 != 0) and (e2 == 0):
                polefacestr = ', e1= '+_np.str(_np.round(e1,4))+' rad'
            elif (e1 == 0) and (e2 != 0):
                polefacestr = ', e2= '+_np.str(_np.round(e2,4))+' rad'
            else:
                polefacestr = ''

            self._printout('\tConverted to:')
            debugstring = 'Dipole '+elementid+', length= '+_np.str(length_in_metres)+' m, angle= '+_np.str(_np.round(angle,4))+' rad'+polefacestr
            self._printout('\t'+debugstring)


    def change_bend(self,linedict):
        '''Function to change the direction of the dipole bend. Can be a direction other than horizontal (i.e != n*pi).
            '''
        ## NOT FULLY TESTED.
        angle = linedict['angle']
        rotation = False
        self.machineprops.angle = _np.float(angle)
        if self.machineprops.angle >= 360:
            self.machineprops.angle = _np.mod(self.machineprops.angle,360)
        if self.machineprops.angle <= -360:
            self.machineprops.angle = _np.mod(self.machineprops.angle,-360)

        if self.machineprops.angle == 180 or self.machineprops.angle == -180: #If 180 degrees, switch bending angle
            self.machineprops.bending *= -1

        
        elif self.machineprops.angle != 0:                        #If not 180 degrees, use transform3d.      
            self.machineprops.angle *= -1                         #For conversion to correct direction. Eg in TRANSPORT -90 is upwards, in BDSIM, 90 is upwards.  
            anginrad = self.machineprops.angle * (_np.pi / 180)
            self.machineprops.transforms += 1
            elementid = 't'+_np.str(self.machineprops.transforms)
            self.gmadmachine.AddTransform3D(name=elementid,psi=anginrad)
            ## MadX Builder does not have transform 3d 
            # Comment out and print warning
            #self.madxmachine.AddTransform3D(name=elementid,psi=anginrad)
            print 'Warning, MadX Builder does not have Transform 3D!'
            
            rotation = True
        
        if self._debug:
            if rotation:
                self._printout('\tConverted to:')
                debugstring = 'Transform3D '+elementid+', angle '+_np.str(_np.round(self.machineprops.angle,4))+' rad'
                self._printout('\t'+debugstring)
            elif self.machineprops.angle == 1:
                self._printout('Bending direction set to Right')
            elif self.machineprops.angle == -1:
                self._printout('Bending direction set to Left')
        


    def quadrupole(self,linedict):
        quaddata = linedict['data']
        length = quaddata[0]        # First three non-blanks must be the entries in a specific order.
        field_at_tip = quaddata[1]  # Field in TRANSPORT units 
        pipe_rad = quaddata[2]      # Pipe Radius In TRANSPORT units
        
        field_in_Gauss = field_at_tip * self.scale[self.units['magnetic_fields'][0]] #Convert to Gauss
        field_in_Tesla = field_in_Gauss * 1e-4  #Convert to Tesla
        
        if self.units['bend_vert_gap'] != 'm':
            pipe_in_metres = pipe_rad * self.scale[self.units['bend_vert_gap'][0]]  #Scale to meters
        else:
            pipe_in_metres = pipe_rad
    
        if self.units['element_length'] != 'm':
            length_in_metres = length * self.scale[self.units['element_length'][0]] #Scale to meters
        else:
            length_in_metres = length
        
        field_gradient = (field_in_Tesla / pipe_in_metres) / self.beamprops.brho    #K1 in correct units
        
        self.machineprops.quads += 1
        #if label is not None: #Write to file
        if field_gradient > 0:
            elementid = 'QF'+_np.str(self.machineprops.quads)
        elif field_gradient < 0:
            elementid = 'QD'+_np.str(self.machineprops.quads)
        else:
            elementid = 'NULLQUAD'+_np.str(self.machineprops.quads)  #For K1 = 0.

        self.gmadmachine.AddQuadrupole(name=elementid,length=length_in_metres,k1=_np.round(field_gradient,4))
        self.madxmachine.AddQuadrupole(name=elementid,length=length_in_metres,k1=_np.round(field_gradient,4))
        
        if self._debug:
            string1 = '\tQuadrupole, field in gauss = ' + _np.str(field_in_Gauss) + ' KG, field in Tesla = ' + _np.str(field_in_Tesla) + ' T.'
            string2 = '\tBeampipe radius = ' + _np.str(pipe_in_metres) + ' m. Field gradient = '+ _np.str(field_in_Tesla/pipe_in_metres) + ' T/m.'
            string3 = '\tBrho = ' + _np.str(_np.round(self.beamprops.brho,4)) + ' Tm. K1 = ' +_np.str(_np.round(field_gradient,4)) + ' m^-2'
            self._printout(string1)
            self._printout(string2)
            self._printout(string3)
            self._printout('\tConverted to:')
            debugstring = 'Quadrupole '+elementid+', length= '+_np.str(length_in_metres)+' m, k1= '+_np.str(_np.round(field_gradient,4))+' T/m'
            self._printout('\t'+debugstring)




    def collimator(self,line):
        label = self._get_label(line)
        ### Was used to write the location of a collimator as a string, redundant if file writing done with pybdsim.
        collstarted = False
        for index in self._collindex: #Look for existing collimator elements of the same name
            if index == label:
                collstarted = True      #If one already exists, that must be the start of the collimator
                break
        
        if collstarted == True:          
            #If the start already exists, input line must be for collimator end
            coll = 'ends'
        else:
            coll = 'starts'
        self._collindex.append(label) #Add to collimator list

        collidata = []
        for index,ele in enumerate(line[1:]): # Iterate over line to extract data
            if ele != '':
                try:
                    collidata.append(_np.float(ele))
                except ValueError:
                    dummy=1

        horwidth = 'Unknown'
        verwidth = 'Unknown'
        # Determine which entry is for horiz. and vert.
        if collidata[0] == 1.0:
            horwidth = _np.str(collidata[1])
        elif collidata[0] == 3.0:
            verwidth = _np.str(collidata[1])

        if len(collidata) > 2:
            if collidata[2] == 1.0:
                horwidth = _np.str(collidata[3])
            elif collidata[2] == 3.0:
                verwidth = _np.str(collidata[3])

        collline  = '! A collimator labelled ' + label +' ' + coll + ' here'
        collline2 = '! with slit size half widths of x = '+horwidth+' '+self.units['x']+' and y = '+verwidth+' '+self.units['x']+'.'


    def acceleration(self,linedict):
        ''' A Function that writes the properties of an acceleration element
            Only RF added for gmad, not for madx!
            '''
        # Redundant function until comments and /or acceleration components can be handled
        
        accdata = linedict['data']

        acclen = accdata[0]
        e_gain = accdata[1]

        # TODO add phase_lag and wavelength

        # protect against zero length
        if acclen == 0.0:
            acclen = 1e-6
        gradient = e_gain * (self.scale[self.units['p_egain'][0]] / 1e6) / (acclen * self.scale[self.units['element_length'][0]]) # gradient in MV/m

        self.machineprops.rf += 1
        elname = "ACC" + _np.str(self.machineprops.rf)

        self.gmadmachine.AddRFCavity(name=elname,length=acclen,gradient=gradient)

        # Update beam parameters
        self._calculate_momentum(self.beamprops.k_energy + e_gain)

        ## Commented out untested code
        #if len(accdata) == 2:       # Newer case with multiple elements
            #self._acc_sequence(line)
        if len(accdata) == 4:     # Older case for single element
            phase_lag = accdata[2]
            wavel = accdata[3]
            
            #Write to file
            accline =  '! An accelerator element goes here of length '+_np.str(acclen)+' '+self.units['element_length']+', \n'
            accline2 = '! with an energy gain of '+_np.str(e_gain)+' '+self.units['p_egain']+', phase lag of '+_np.str(phase_lag)+' degrees, \n'
            accline3 = '! and a wavelength of '+_np.str(wavel)+' '+_self.units['bunch_length']+'. \n'


    def _acc_sequence(self,inputline):
        '''Function to calculate the total length of a sequence of accelerator components.
            '''
        ## UNTESTED ##
        
        # Redundant function until comments and /or acceleration components can be handled.
        concat=''
        for ele in inputline:                       #Concat string back together
            concat += ele
            if ele != inputline[-1]:
                concat += ' '
        ele=0
        for linenum,line in enumerate(self.data):   #Find start of accelerator element sequence
            if line == concat:
                seq_start = linenum
                break
        accparts=[]
        accelements = 0
        isacc = True
        while isacc:                                #Find remainder of acc sequence
            a = self.data[seq_start+accelements].split(' ')
            if a[0] == '11.':
                accparts.append(a)
                accelements += 1
            else:
                isacc = False
        acccopy = accparts #temp copy of data
        accparts=[]
        for part in acccopy:               #Calculate total length of accelerator part.
            accdata=[]
            for index,ele in enumerate(part[1:]):
                if ele != '':
                    try:
                        accdata.append(_np.float(ele))
                    except ValueError:
                        pass
            accparts.append(accdata)
        accarray = _np.array(accparts)
        tot_len = _np.sum(accarray[2:,0])
        #Write to file
        accline = '! An electrostatic accelerator section goes here, of length '+_np.str(tot_len)+' '+self.units['element_length']+','
        accline2= '!split into '+_np.str(accelements-1)+' elements, with a total voltage of '+_np.str(_np.round(accarray[0,1],3))+' GV.'



    def sextupole(self,linedict):
        sextudata = linedict['data']
        length = sextudata[0]        # First three non-blanks must be the entries in a specific order.
        field_at_tip = sextudata[1]  # Field in TRANSPORT units
        pipe_rad = sextudata[2]      # Pipe Radius In TRANSPORT units
        
        field_in_Gauss = field_at_tip * self.scale[self.units['magnetic_fields'][0]] #Convert to Gauss
        field_in_Tesla = field_in_Gauss * 1e-4  #Convert to Tesla
        
        if self.units['bend_vert_gap'] != 'm':
            pipe_in_metres = pipe_rad * self.scale[self.units['bend_vert_gap'][0]]  #Scale to meters
        else:
            pipe_in_metres = pipe_rad
        
        if self.units['element_length'] != 'm':
            length_in_metres = length * self.scale[self.units['element_length'][0]] #Scale to meters
        else:
            length_in_metres = length
        
        field_gradient = (2*field_in_Tesla / pipe_in_metres**2) / self.beamprops.brho    #K2 in correct units
        
        self.machineprops.sextus += 1
        elementid = 'SEXT'+_np.str(self.machineprops.sextus)
        
        self.gmadmachine.AddSextupole(name=elementid,length=length_in_metres,k2=_np.round(field_gradient,4))
        self.madxmachine.AddSextupole(name=elementid,length=length_in_metres,k2=_np.round(field_gradient,4))


        if self._debug:
            self._printout('\tConverted to:')
            debugstring = 'Sextupole '+elementid+', length '+_np.str(length_in_metres)+' m, k2 '+_np.str(_np.round(field_gradient,4))+' T/m^2'
            self._printout('\t'+debugstring)



    def solenoid(self,linedict):
        soledata = linedict['data']
        length = soledata[0]        # First three non-blanks must be the entries in a specific order.
        field = soledata[1]         # Field in TRANSPORT units
        
        field_in_Gauss = field * self.scale[self.units['magnetic_fields'][0]] #Convert to Gauss
        field_in_Tesla = field_in_Gauss * 1e-4  #Convert to Tesla
        
        if self.units['element_length'] != 'm':
            length_in_metres = length * self.scale[self.units['element_length'][0]] #Scale to meters
        else:
            length_in_metres = length
                
        self.machineprops.solenoids += 1
        elementid = 'SOLE'+_np.str(self.machineprops.solenoids)
        
        self.gmadmachine.AddSolenoid(name=elementid,length=length_in_metres,ks=_np.round(field_in_Tesla,4))
        self.madxmachine.AddSolenoid(name=elementid,length=length_in_metres,ks=_np.round(field_in_Tesla,4))

        if self._debug:
            self._printout('\tConverted to:')
            debugstring = 'Solenoid '+elementid+', length '+_np.str(length_in_metres)+' m, ks '+_np.str(_np.round(field_in_Tesla,4))+' T'
            self._printout('\t'+debugstring)


    def printline(self,linedict):
        number = linedict['data'][0]
#        for ele in line[1:]:
        try:
            number = _np.float(number)
            if number == 48:
                self.machineprops.benddef = False
                self._printout('Switched Dipoles to Angle definition.')
            if number == 47:
                self.machineprops.benddef = True
                self._printout('Switched Dipoles to field definition.')
        except ValueError:
            pass


    def correction(self,linedict):
        if self._correctedbeamdef == True:
            self._printout('\t Not Correction to original beam definition')
            return
        #Check if the previous line was the original beam definition and not an rms update
        if linedict['prevlinenum'] == 1.0 and not linedict['isAddition'] and self._beamdefined:
            self._correctedbeamdef = True
        
        correctiondata = linedict['data']
        if len(correctiondata) >= 15: #15 sigma elements
            sigma21 = correctiondata[0]
            sigma43 = correctiondata[5]
        else:
            self._printout('\tLength of correction line is incorrect')
            return

        emittoverbeta = self.beamprops.SigmaXP**2 * (1 - sigma21**2)
        emittbeta = self.beamprops.SigmaX**2
        betx = _np.sqrt(emittbeta / emittoverbeta)
        emitx = emittbeta / betx
        slope = sigma21 * self.beamprops.SigmaXP / self.beamprops.SigmaX
        alfx = -1.0 * slope * betx
        
        self.beamprops.betx = betx
        self.beamprops.emitx = emitx / 1000.0
        self.beamprops.alfx = alfx
        
        emittoverbeta = self.beamprops.SigmaYP**2 * (1 - sigma43**2)
        emittbeta = self.beamprops.SigmaY**2
        bety = _np.sqrt(emittbeta / emittoverbeta)
        emity = emittbeta / bety
        slope = sigma43 * self.beamprops.SigmaYP / self.beamprops.SigmaY
        alfy = -1.0 * slope * bety

        self.beamprops.bety = bety
        self.beamprops.emity = emity / 1000.0
        self.beamprops.alfy = alfy

        self.beamprops.distrType = 'gausstwiss'

        if self._debug:
            self._printout('\tConverted to:')
            self._printout('\t Beam Correction. Sigma21 = ' + _np.str(sigma21) + ', Sigma43 = '  + _np.str(sigma43) + '.')
            self._printout('\t Beam distribution type now switched to "gausstwiss":')
            self._printout('\t Twiss Params:')
            self._printout('\t BetaX = ' +_np.str(self.beamprops.betx) + ' ' + self.units['beta_func'])
            self._printout('\t BetaY = ' +_np.str(self.beamprops.bety) + ' ' + self.units['beta_func'])
            self._printout('\t AlphaX = '+_np.str(self.beamprops.alfx))
            self._printout('\t AlphaY = '+_np.str(self.beamprops.alfy))
            self._printout('\t Emittx = '+_np.str(self.beamprops.emitx) + ' ' + self.units['emittance'])
            self._printout('\t EmittY = '+_np.str(self.beamprops.emity) + ' ' + self.units['emittance'])



    def special_input(self,linedict):
        specialdata = linedict['data']

        if specialdata[0] == 16.0:  #X0 offset
            self.beamprops.X0 = specialdata[1]
        if specialdata[0] == 17.0:  #Y0 offset
            self.beamprops.Y0 = specialdata[1]
        if specialdata[0] == 18.0:  #Z0 offset
            self.beamprops.Z0 = specialdata[1]
        #if specialdata[0] == 5.0:   #beampiperadius (technically only vertical, but will apply a circle for now)
        #    self.machineprops.beampiperadius = specialdata[1]

        #if self._debug:
        #    self._printout('\tConverted to:')
        #    self._printout('\t'+_np.str(specialdata[2]))

