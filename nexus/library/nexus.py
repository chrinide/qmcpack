##################################################################
##  (c) Copyright 2015-  by Jaron T. Krogel                     ##
##################################################################


#====================================================================#
#  nexus.py                                                          #
#    Gathering place for user-facing Nexus functions.  Management    #
#    of user-provided settings.                                      #
#                                                                    #
#  Content summary:                                                  #
#    Settings                                                        #
#      Class to set 'global' Nexus data.                             #
#                                                                    #
#    settings                                                        #
#      A single Settings instance users interact with as a function. #
#                                                                    #
#    run_project                                                     #
#      User interface to the ProjectManager.                         #
#      Runs all simulations generated by the user.                   #
#                                                                    #
#====================================================================#


import os

from generic import obj

from nexus_base      import NexusCore,nexus_core,nexus_noncore,nexus_core_noncore
from machines        import Job,job,Machine,Supercomputer,get_machine
from simulation      import generate_simulation,input_template,multi_input_template,generate_template_input,generate_multi_template_input
from project_manager import ProjectManager

from structure       import Structure,generate_structure,generate_cell,read_structure
from physical_system import PhysicalSystem,generate_physical_system
from pseudopotential import Pseudopotential,Pseudopotentials
from basisset        import BasisSets
from bundle          import bundle

from opium   import Opium  , OpiumInput  , OpiumAnalyzer
from sqd     import Sqd    , SqdInput    , SqdAnalyzer    , generate_sqd_input    , generate_sqd, hunds_rule_filling
from pwscf   import Pwscf  , PwscfInput  , PwscfAnalyzer  , generate_pwscf_input  , generate_pwscf
from gamess  import Gamess , GamessInput , GamessAnalyzer , generate_gamess_input , generate_gamess, FormattedGroup
from vasp    import Vasp   , VaspInput   , VaspAnalyzer   , generate_vasp_input   , generate_vasp
from qmcpack import Qmcpack, QmcpackInput, QmcpackAnalyzer, generate_qmcpack_input, generate_qmcpack

from qmcpack_converters import Pw2qmcpack , Pw2qmcpackInput , Pw2qmcpackAnalyzer , generate_pw2qmcpack_input , generate_pw2qmcpack
from qmcpack_converters import Wfconvert  , WfconvertInput  , WfconvertAnalyzer  , generate_wfconvert_input  , generate_wfconvert
from qmcpack_converters import Convert4qmc, Convert4qmcInput, Convert4qmcAnalyzer, generate_convert4qmc_input, generate_convert4qmc
from pw2casino          import Pw2casino  , Pw2casinoInput  , Pw2casinoAnalyzer  , generate_pw2casino_input  , generate_pw2casino

from pwscf_postprocessors import PP      , PPInput      , PPAnalyzer      , generate_pp_input      , generate_pp
from pwscf_postprocessors import Dos     , DosInput     , DosAnalyzer     , generate_dos_input     , generate_dos
from pwscf_postprocessors import Bands   , BandsInput   , BandsAnalyzer   , generate_bands_input   , generate_bands
from pwscf_postprocessors import Projwfc , ProjwfcInput , ProjwfcAnalyzer , generate_projwfc_input , generate_projwfc
from pwscf_postprocessors import Cppp    , CpppInput    , CpppAnalyzer    , generate_cppp_input    , generate_cppp
from pwscf_postprocessors import Pwexport, PwexportInput, PwexportAnalyzer, generate_pwexport_input, generate_pwexport

from qmcpack import loop,linear,cslinear,vmc,dmc
from qmcpack import generate_jastrows,generate_jastrow,generate_jastrow1,generate_jastrow2,generate_jastrow3,generate_opt,generate_opts
from qmcpack import generate_cusp_correction

from debug import *


#set the machine if known, otherwise user will provide
hostmachine = Machine.get_hostname()
if Machine.exists(hostmachine):
    Job.machine = hostmachine
    ProjectManager.machine = Machine.get(hostmachine)
#end if



class Settings(NexusCore):
    singleton = None

    machine_vars = set('''
        machine         account         machine_info    interactive_cores
        machine_mode
        '''.split())

    core_assign_vars = set('''
        status_only     generate_only   runs            results 
        pseudo_dir      sleep           local_directory remote_directory 
        monitor         skip_submit     load_images     stages          
        verbose         debug           trace
        '''.split())

    core_process_vars = set('''
        file_locations  mode  status
        '''.split())

    noncore_assign_vars = set('''
        basis_dir
        '''.split())

    noncore_process_vars = set()
    
    gamess_vars  = set('''
        ericfmt         mcppath
        '''.split())

    pwscf_vars   = set('''
        vdw_table
        '''.split())
    
    nexus_core_vars    = core_assign_vars    | core_process_vars
    nexus_noncore_vars = noncore_assign_vars | noncore_process_vars
    nexus_vars         = nexus_core_vars     | nexus_noncore_vars
    allowed_vars       = nexus_vars | machine_vars | gamess_vars | pwscf_vars


    @staticmethod
    def kw_set(vars,source=None):
        kw = obj()
        if source!=None:
            for n in vars:
                if n in source:
                    kw[n]=source[n]
                    del source[n]
                #end if
            #end for
        #end if
        return kw
    #end def null_kw_set


    def __init__(self):
        if Settings.singleton is None:
            Settings.singleton = self
        else:
            self.error('attempted to create a second Settings object\n  please just use the original')
        #end if
    #end def __init__


    def error(self,message,header='settings',exit=True,trace=True):
        NexusCore.error(self,message,header,exit,trace)
    #end def error


    # sets up Nexus core class behavior and passes information to broader class structure
    def __call__(self,**kwargs):

        NexusCore.write_splash()

        self.log('Applying user settings')

        # guard against invalid settings
        not_allowed = set(kwargs.keys()) - Settings.allowed_vars
        if len(not_allowed)>0:
            self.error('unrecognized variables provided\nyou provided: {0}\nallowed variables are: {1}'.format(sorted(not_allowed),sorted(Settings.allowed_vars)))
        #end if

        # assign simple variables
        for name in Settings.core_assign_vars:
            if name in kwargs:
                nexus_core[name] = kwargs[name]
            #end if
        #end for

        # assign simple variables
        for name in Settings.noncore_assign_vars:
            if name in kwargs:
                nexus_noncore[name] = kwargs[name]
            #end if
        #end for

        # extract settings based on keyword groups
        kw        = Settings.kw_set(Settings.nexus_vars  ,kwargs)   
        mach_kw   = Settings.kw_set(Settings.machine_vars,kwargs)      
        gamess_kw = Settings.kw_set(Settings.gamess_vars ,kwargs)       
        pwscf_kw  = Settings.kw_set(Settings.pwscf_vars  ,kwargs)
        if len(kwargs)>0:
            self.error('some settings keywords have not been accounted for\nleftover keywords: {0}\nthis is a developer error'.format(sorted(kwargs.keys())))
        #end if


        # copy input settings
        self.transfer_from(mach_kw.copy())
        self.transfer_from(gamess_kw.copy())
        self.transfer_from(pwscf_kw.copy())

        # process machine settings
        self.process_machine_settings(mach_kw)

        # process nexus core settings
        self.process_core_settings(kw)

        # process nexus noncore settings
        self.process_noncore_settings(kw)

        # transfer select core data to the global namespace
        nexus_core_noncore.transfer_from(nexus_core,nexus_core_noncore.keys())
        nexus_noncore.set(**nexus_core_noncore.copy()) # prevent write to core namespace

        # copy final core and noncore settings
        self.transfer_from(nexus_core.copy())
        self.transfer_from(nexus_noncore.copy())


        # process gamess settings
        Gamess.settings(**gamess_kw)

        # process pwscf settings
        Pwscf.settings(**pwscf_kw)

        return
    #end def __call__


    def process_machine_settings(self,mset):
        if 'machine_info' in mset:
            machine_info = mset.machine_info
            if isinstance(machine_info,dict) or isinstance(machine_info,obj):
                for machine_name,minfo in machine_info.iteritems():
                    mname = machine_name.lower()
                    if Machine.exists(mname):
                        machine = Machine.get(mname)
                        machine.incorporate_user_info(minfo)
                    else:
                        self.error('machine {0} is unknown\n  cannot set machine_info'.format(machine_name))
                    #end if
                #end for
            else:
                self.error('machine_info must be a dict or obj\n  you provided type '+machine_info.__class__.__name__)
            #end if
        #end if
        if 'machine' in mset:
            machine_name = mset.machine
            if not Machine.exists(machine_name):
                self.error('machine {0} is unknown'.format(machine_name))
            #end if
            Job.machine = machine_name
            ProjectManager.machine = Machine.get(machine_name)
            if 'account' in mset:
                account = mset.account
                if not isinstance(account,str):
                    self.error('account for {0} must be a string\n  you provided: {1}'.format(machine_name,account))
                #end if
                ProjectManager.machine.account = account
            #end if
            if 'machine_mode' in mset:
                machine_mode = mset.machine_mode
                if machine_mode in Machine.modes:
                    machine_mode = Machine.modes[machine_mode]
                #end if
                if machine_mode==Machine.modes.interactive:
                    if ProjectManager.machine==None:
                        ProjectManager.class_error('no machine specified for interactive mode')
                    #end if
                    if not isinstance(ProjectManager.machine,Supercomputer):
                        self.error('interactive mode is not supported for machine type '+ProjectManager.machine.__class__.__name__)
                    #end if
                    if not 'interactive_cores' in mset:
                        self.error('interactive mode requested, but interactive_cores not set')
                    #end if
                    ProjectManager.machine = ProjectManager.machine.interactive_representation(mset.interactive_cores)
                    Job.machine = ProjectManager.machine.name
                #end if
            #end if
        #end if
    #end def process_machine_settings


    def process_core_settings(self,kw):
        # process project manager settings
        if nexus_core.debug:
            nexus_core.verbose = True
        #end if
        if 'status' in kw:
            if kw.status==None or kw.status==False:
                nexus_core.status = nexus_core.status_modes.none
            elif kw.status==True:
                nexus_core.status = nexus_core.status_modes.standard
            elif kw.status in nexus_core.status_modes:
                nexus_core.status = nexus_core.status_modes[kw.status]
            else:
                self.error('invalid status mode specified: {0}\nvalid status modes are: {1}'.format(kw.status,sorted(nexus_core.status_modes.keys())))
            #end if
        #end if
        if nexus_core.status_only and nexus_core.status==nexus_core.status_modes.none:
            nexus_core.status = nexus_core.status_modes.standard
        #end if
        if 'mode' in kw:
            if kw.mode in nexus_core.modes:
                nexus_core.mode = kw.mode
            else:
                self.error('invalid mode specified: {0}\nvalid modes are: {1}'.format(kw.mode,sorted(nexus_core.modes.keys())))
            #end if
        #end if
        mode  = nexus_core.mode
        modes = nexus_core.modes
        if mode==modes.stages:
            stages = nexus_core.stages
        elif mode==modes.all:
            stages = list(nexus_core.primary_modes)
        else:
            stages = [kw.mode]
        #end if
        allowed_stages = set(nexus_core.primary_modes)
        if isinstance(stages,str):
            stages = [stages]
        #end if
        if len(stages)==0:
            stages = list(nexus_core.primary_modes)
        elif 'all' in stages:
            stages = list(nexus_core.primary_modes)
        else:
            forbidden = set(nexus_core.stages)-allowed_stages
            if len(forbidden)>0:
                self.error('some stages provided are not primary stages.\n  You provided '+str(list(forbidden))+'\n  Options are '+str(list(allowed_stages)))
            #end if
        #end if
        # overide user input and always use stages mode 
        # keep processing code above in case a change is desired in the future
        nexus_core.mode       = modes.stages
        nexus_core.stages     = stages
        nexus_core.stages_set = set(nexus_core.stages)

        # process simulation settings
        if 'local_directory' in kw:
            nexus_core.file_locations.append(kw.local_directory)
        #end if
        if 'file_locations' in kw:
            fl = kw.file_locations
            if isinstance(fl,str):
                nexus_core.file_locations.extend([fl])
            else:
                nexus_core.file_locations.extend(list(fl))
            #end if
        #end if
        if not 'pseudo_dir' in kw:
            nexus_core.pseudopotentials = Pseudopotentials()
        else:
            pseudo_dir = kw.pseudo_dir
            nexus_core.file_locations.append(pseudo_dir)
            if not os.path.exists(pseudo_dir):
                self.error('pseudo_dir "{0}" does not exist'.format(pseudo_dir),trace=False)
            #end if
            files = os.listdir(pseudo_dir)
            ppfiles = []
            for f in files:
                pf = os.path.join(pseudo_dir,f)
                if os.path.isfile(pf):
                    ppfiles.append(pf)
                #end if
            #end for
            nexus_core.pseudopotentials = Pseudopotentials(ppfiles)        
        #end if
    #end def process_core_settings


    def process_noncore_settings(self,kw):
        if not 'basis_dir' in kw:
            nexus_noncore.basissets = BasisSets()
        else:
            basis_dir = kw.basis_dir
            nexus_core.file_locations.append(basis_dir)
            if not os.path.exists(basis_dir):
                self.error('basis_dir "{0}" does not exist'.format(basis_dir),trace=False)
            #end if
            files = os.listdir(basis_dir)
            bsfiles = []
            for f in files:
                pf = os.path.join(basis_dir,f)
                if os.path.isfile(pf):
                    bsfiles.append(pf)
                #end if
            #end for
            nexus_noncore.basissets = BasisSets(bsfiles)        
        #end if
    #end def process_noncore_settings
#end class Settings


# create settings functor for UI
settings = Settings()


def run_project(*args,**kwargs):
    pm = ProjectManager()
    pm.add_simulations(*args,**kwargs)
    pm.run_project()
#end def run_project
