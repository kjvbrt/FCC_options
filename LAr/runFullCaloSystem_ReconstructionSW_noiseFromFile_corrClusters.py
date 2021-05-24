# Setup
# Names of cells collections
ecalBarrelCellsName = "ECalBarrelCells"
# Readouts
ecalBarrelReadoutName = "ECalBarrelPhiEta"

# Number of events
num_events = -1

from Gaudi.Configuration import INFO, WARNING
from Configurables import ApplicationMgr, FCCDataSvc, PodioOutput
import os

podioevent = FCCDataSvc("EventDataSvc")
import glob
podioevent.inputs = glob.glob("output_fullCalo_SimAndDigi_*.root")
# reads HepMC text file and write the HepMC::GenEvent to the data service
from Configurables import PodioInput
podio_input = PodioInput("podioReader",
                         collections=[ecalBarrelCellsName,
                                      "GenParticles"])


from Configurables import GeoSvc
geo_service = GeoSvc("GeoSvc")
# if FCC_DETECTORS is empty, this should use relative path to working directory
path_to_detector = os.environ.get("FCCDETECTORS", "")
print("INFO: " + path_to_detector)
detectors_to_use = ['Detector/DetFCCeeIDEA-LAr/compact/FCCee_DectMaster.xml']
# prefix all xmls with path_to_detector
geo_service.detectors = [os.path.join(path_to_detector, _det) for _det in detectors_to_use]
geo_service.OutputLevel = WARNING


ecalBarrelNoisePath = "http://fccsw.web.cern.ch/fccsw/testsamples/"
ecalBarrelNoisePath += "elecNoise_ecalBarrelFCCee_50Ohm_traces1_4shieldWidth.root"
ecalBarrelNoiseHistName = "h_elecNoise_fcc_"

# add noise, create all existing cells in detector
from Configurables import NoiseCaloCellsFromFileTool
noiseBarrel = NoiseCaloCellsFromFileTool("NoiseBarrel",
                                         readoutName=ecalBarrelReadoutName,
                                         noiseFileName=ecalBarrelNoisePath,
                                         elecNoiseHistoName=ecalBarrelNoiseHistName,
                                         activeFieldName="layer",
                                         addPileup=False,
                                         numRadialLayers=8)
from Configurables import TubeLayerPhiEtaCaloTool
barrelGeometry = TubeLayerPhiEtaCaloTool("EcalBarrelGeo",
                                         readoutName=ecalBarrelReadoutName,
                                         activeVolumeName="LAr_sensitive",
                                         activeFieldName="layer",
                                         fieldNames=["system"],
                                         fieldValues=[4],
                                         activeVolumesNumber=8)
from Configurables import CreateCaloCells
createEcalBarrelCells = CreateCaloCells("CreateECalBarrelCells",
                                        geometryTool=barrelGeometry,
                                        doCellCalibration=False,  # already calibrated
                                        addCellNoise=True, filterCellNoise=False,
                                        noiseTool=noiseBarrel,
                                        hits=ecalBarrelCellsName,
                                        cells=ecalBarrelCellsName+"Noise",
                                        OutputLevel=INFO)

#Empty cells for parts of calorimeter not implemented yet
from Configurables import CreateEmptyCaloCellsCollection
create_empty_cells = CreateEmptyCaloCellsCollection("CreateEmptyCaloCells")
create_empty_cells.cells.Path = "emptyCaloCells"

#Create calorimeter clusters
from GaudiKernel.PhysicalConstants import pi

from Configurables import CaloTowerTool
towers = CaloTowerTool("towers",
                       deltaEtaTower=0.01, deltaPhiTower=2*pi/704.,
                       ecalBarrelReadoutName=ecalBarrelReadoutName,
                       ecalEndcapReadoutName="",
                       ecalFwdReadoutName="",
                       hcalBarrelReadoutName="",
                       hcalExtBarrelReadoutName="",
                       hcalEndcapReadoutName="",
                       hcalFwdReadoutName="",
                       OutputLevel=INFO)
towers.ecalBarrelCells.Path = ecalBarrelCellsName + "Noise"
towers.ecalEndcapCells.Path = "emptyCaloCells"
towers.ecalFwdCells.Path = "emptyCaloCells"
towers.hcalBarrelCells.Path = "emptyCaloCells"
towers.hcalExtBarrelCells.Path = "emptyCaloCells"
towers.hcalEndcapCells.Path = "emptyCaloCells"
towers.hcalFwdCells.Path = "emptyCaloCells"

# Cluster variables
windE = 9
windP = 17
posE = 5
posP = 11
dupE = 7
dupP = 13
finE = 9
finP = 17
# approx in GeV: changed from default of 12 in FCC-hh
threshold = 2

from Configurables import CreateCaloClustersSlidingWindow
createClusters = CreateCaloClustersSlidingWindow("CreateClusters",
                                                 towerTool=towers,
                                                 nEtaWindow=windE, nPhiWindow=windP,
                                                 nEtaPosition=posE, nPhiPosition=posP,
                                                 nEtaDuplicates=dupE, nPhiDuplicates=dupP,
                                                 nEtaFinal=finE, nPhiFinal=finP,
                                                 energyThreshold=threshold,
                                                 attachCells=True
                                                 )
createClusters.clusters.Path = "CaloClusters"
createClusters.clusterCells.Path = "CaloClusterCells"


# Correct calorimeter clusters
from Configurables import CorrectCaloClusters
upsilonFormulas = [["[0] + [1]/(x-[2]) + [3]/y + [4]*x*y",
                    "[0] + [1]*x + [2]*y"]]
upsilonParams = [[0.19273955, -93.537587, -502.03357, 1.6392139, -6.6680416e-07,
                  1.5552395, 0.0014413861, -0.0029812944]]
deltaFormulas = [["[0] + [1]*x + [2]*y + [3]*x*y",
                  "[0] + [1]/x + [2]*y + [3]*y*x",
                  "[0] + [1]/x + [2]*y + [3]*y/x"]]
deltaParams = [[0.011630701, -0.011286394, -0.00016897777, 0.00024319390,
                0.84463331, -1.4287416, 0.0034946740, 3.3325244e-05,
                -0.010155463, -0.0054047813, 0.00041343349, 0.10544402]]
corr_clusters = CorrectCaloClusters("corrClusters",
                                    inClusters="CaloClusters",
                                    outClusters="CaloClustersCorrected",
                                    upstreamFormulas=upsilonFormulas,
                                    upstreamParameters=upsilonParams,
                                    downstreamFormulas=deltaFormulas,
                                    downstreamParameters=deltaParams,
                                    # OutputLevel=VERBOSE)
                                    OutputLevel=INFO)


import uuid
podio_output = PodioOutput("podioOutput",
                           filename="output_allCalo_reco_noise_" + uuid.uuid4().hex + ".root")
podio_output.outputCommands = ["keep *"]

#CPU information
from Configurables import AuditorSvc, ChronoAuditor
chra = ChronoAuditor()
audsvc = AuditorSvc()
audsvc.Auditors = [chra]
podio_input.AuditExecute = True
createClusters.AuditExecute = True
podio_output.AuditExecute = True

ApplicationMgr(
    TopAlg=[podio_input,
            create_empty_cells,
            createEcalBarrelCells,
            createClusters,
            corr_clusters,
            podio_output
            ],
    EvtSel='NONE',
    EvtMax=num_events,
    ExtSvc=[podioevent, geo_service])
