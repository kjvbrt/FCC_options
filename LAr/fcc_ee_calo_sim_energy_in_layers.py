from Gaudi.Configuration import WARNING, VERBOSE

# Electron momentum in GeV
momentum = 50
# Theta and its spread in degrees
theta = 90.
thetaSpread = 10.

samplingFractions = [0.303451138049] * 1 + [0.111872504159] * 1 + [0.135806495306] * 1 + [0.151772636618] * 1 + \
                    [0.163397436122] * 1 + [0.172566977313] * 1 + [0.179855253903] * 1 + [0.186838417657] * 1 + \
                    [0.192865946689] * 1 + [0.197420241611] * 1 + [0.202066552306] * 1 + [0.22646764465] * 1

#----------------------------------------------------------------------------------------------------------------------

# Data service
from Configurables import FCCDataSvc
podioevent = FCCDataSvc("EventDataSvc")

# Particle gun setup
from Configurables import MomentumRangeParticleGun
from GaudiKernel.SystemOfUnits import GeV
from math import pi

pgun = MomentumRangeParticleGun("ParticleGun_Electron")
pgun.PdgCodes = [11]
pgun.MomentumMin = momentum * GeV
pgun.MomentumMax = momentum * GeV
pgun.PhiMin = 0
pgun.PhiMax = 2 * pi
# theta = 90 degrees (eta = 0)
pgun.ThetaMin = (theta - thetaSpread/2) * pi / 180.
pgun.ThetaMax = (theta + thetaSpread/2) * pi / 180.

from Configurables import GenAlg
genalg_pgun = GenAlg()
genalg_pgun.SignalProvider = pgun
genalg_pgun.hepmc.Path = "hepmc"

from Configurables import HepMCToEDMConverter
hepmc_converter = HepMCToEDMConverter()
hepmc_converter.hepmc.Path = "hepmc"
hepmc_converter.GenParticles.Path = "GenParticles"

# DD4hep geometry service
from Configurables import GeoSvc
from os import environ, path
detector_path = environ.get("FCCDETECTORS", "")
detectors = ['Detector/DetFCCeeIDEA-LAr/compact/FCCee_DectEmptyMaster.xml',
             'Detector/DetFCCeeECalInclined/compact/FCCee_ECalBarrel_deadMaterial.xml']
geoservice = GeoSvc("GeoSvc",
                    detectors=[path.join(detector_path, detector) for detector in detectors],
                    OutputLevel=WARNING)

# Geant4 service
# Configures the Geant simulation: geometry, physics list and user actions
from Configurables import SimG4Svc
geantservice = SimG4Svc("SimG4Svc",
                        detector='SimG4DD4hepDetector',
                        physicslist="SimG4FtfpBert",
                        actions="SimG4FullSimActions")
geantservice.g4PostInitCommands += ["/run/setCut 0.1 mm"]

# Geant4 algorithm
# Translates EDM to G4Event, passes the event to G4, writes out outputs via tools
# and a tool that saves the calorimeter hits
from Configurables import SimG4Alg, SimG4SaveCalHits
saveecaltool = SimG4SaveCalHits("saveECalBarrelHits",
                                readoutNames=["ECalBarrelEta"])
saveecaltool.CaloHits.Path = "ECalBarrelHits"

from Configurables import SimG4PrimariesFromEdmTool
particle_converter = SimG4PrimariesFromEdmTool("EdmConverter")
particle_converter.GenParticles.Path = "GenParticles"

# next, create the G4 algorithm, giving the list of names of tools ("XX/YY")
geantsim = SimG4Alg("SimG4Alg",
                    outputs=[saveecaltool],
                    eventProvider=particle_converter)

# Create calorimeter cells from calorimeter hits
from Configurables import CreateCaloCells
createcellsBarrel = CreateCaloCells("CreateCaloCellsBarrel",
                                    doCellCalibration=False,
                                    addCellNoise=False,
                                    filterCellNoise=False)
createcellsBarrel.hits.Path = "ECalBarrelHits"
createcellsBarrel.cells.Path = "ECalBarrelCells"

# Determine energy deposited in every calorimeter layer
from Configurables import EnergyInCaloLayers
caloLayers = EnergyInCaloLayers("caloLayers",
                                readoutName="ECalBarrelEta",
                                numLayers=12,
                                # sampling fraction is given as the energy correction will be applied on calibrated
                                # cells
                                samplingFractions=samplingFractions,
                                OutputLevel=VERBOSE)
caloLayers.deposits.Path = "ECalBarrelCells"
caloLayers.particle.Path = "GenParticles"

# Print CPU information
from Configurables import AuditorSvc, ChronoAuditor
chra = ChronoAuditor()
audsvc = AuditorSvc()
audsvc.Auditors = [chra]
geantsim.AuditExecute = True
caloLayers.AuditExecute = True

# PODIO output
from Configurables import PodioOutput
import uuid
podio_out = PodioOutput("PodioOut",)
podio_out.outputCommands = ["drop *", "keep energyInLayer", "keep energyInCryo", ]
podio_out.filename = "fccee_energyInCaloLayers_%ideg_%igev_%s.root" % (theta, momentum, uuid.uuid4().hex[0:16])

# ApplicationMgr
from Configurables import ApplicationMgr
ApplicationMgr(TopAlg=[genalg_pgun,
                       hepmc_converter,
                       geantsim,
                       createcellsBarrel,
                       caloLayers,
                       podio_out],
               EvtSel='NONE',
               EvtMax=10,
               # order is important, as GeoSvc is needed by G4SimSvc
               ExtSvc=[podioevent,
                       geoservice,
                       geantservice,
                       audsvc]
               )
