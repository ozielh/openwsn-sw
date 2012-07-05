
import logging
class NullHandler(logging.Handler):
    def emit(self, record):
        pass
log = logging.getLogger('moteState')
log.setLevel(logging.ERROR)
log.addHandler(NullHandler())

import copy
import time
import threading
import pprint

from moteConnector import ParserStatus
from moteConnector import MoteConnectorConsumer
from openType      import typeAsn,     \
                          typeAddr,    \
                          typeCellType

class StateElem(object):
    
    def __init__(self):
        self.meta                      = [{}]
        self.data                      = []
        
        self.meta[0]['numUpdates']     = 0
    
    def update(self):
        self.meta[0]['lastUpdated']    = time.time()
        self.meta[0]['numUpdates']    += 1
    
    def getData(self):
        
        returnVal = {}
        returnVal['meta'] = copy.deepcopy(self.meta)
        returnVal['data'] = []
        for rowNum in range(len(self.data)):
            if   isinstance(self.data[rowNum],dict):
                returnVal['data'].append({})
                for k,v in self.data[rowNum].items():
                    if isinstance(v,(list, tuple)):
                        returnVal['data'][-1][k] = [m.getData() for m in v]
                    else:
                        returnVal['data'][-1][k] = v
            elif isinstance(self.data[rowNum],StateElem):
                parsedRow = self.data[rowNum].getData()
                assert('data' in parsedRow)
                assert(len(parsedRow['data'])<2)
                if len(parsedRow['data'])==1:
                    returnVal['data'].append(parsedRow['data'][0])
            else:
                raise SystemError("can not parse elem of type {0}".format(type(self.data[rowNum])))
        
        return returnVal
    
    def __str__(self):
        pp = pprint.PrettyPrinter(indent=3)
        return pp.pformat(self.getData())

class StateOutputBuffer(StateElem):
    
    def update(self,notif):
        StateElem.update(self)
        if len(self.data)==0:
            self.data.append({})
        self.data[0]['index_write']    = notif.index_write
        self.data[0]['index_read']     = notif.index_read

class StateAsn(StateElem):
    
    def update(self,notif):
        StateElem.update(self)
        if len(self.data)==0:
            self.data.append({})
        if 'asn' not in self.data[0]:
            self.data[0]['asn']        = typeAsn.typeAsn()
        self.data[0]['asn'].update(notif.asn_0_1,
                                   notif.asn_2_3,
                                   notif.asn_4)

class StateMacStats(StateElem):
    
    def update(self,notif):
        StateElem.update(self)
        if len(self.data)==0:
            self.data.append({})
        self.data[0]['syncCounter']    = notif.syncCounter
        self.data[0]['minCorrection']  = notif.minCorrection
        self.data[0]['maxCorrection']  = notif.maxCorrection
        self.data[0]['numDeSync']      = notif.numDeSync

class StateScheduleRow(StateElem):

    def update(self,notif):
        StateElem.update(self)
        if len(self.data)==0:
            self.data.append({})
        self.data[0]['slotOffset']     = notif.slotOffset
        if 'type' not in self.data[0]:
            self.data[0]['type']       = typeCellType.typeCellType()
        self.data[0]['type'].update(notif.type)
        self.data[0]['shared']         = notif.shared
        self.data[0]['channelOffset']  = notif.channelOffset
        if 'neighbor' not in self.data[0]:
            self.data[0]['neighbor']   = typeAddr.typeAddr()
        self.data[0]['neighbor'].update(notif.neighbor_type,
                                        notif.neighbor_bodyH,
                                        notif.neighbor_bodyL)
        self.data[0]['backoffExponent']= notif.backoffExponent
        self.data[0]['backoff']        = notif.backoff
        self.data[0]['numRx']          = notif.numRx
        self.data[0]['numTx']          = notif.numTx
        self.data[0]['numTxACK']       = notif.numTxACK
        if 'lastUsedAsn' not in self.data[0]:
            self.data[0]['lastUsedAsn']=typeAsn.typeAsn()
        self.data[0]['lastUsedAsn'].update(notif.lastUsedAsn_0_1,
                                           notif.lastUsedAsn_2_3,
                                           notif.lastUsedAsn_4)

class StateQueueRow(StateElem):
    
    def update(self,creator,owner):
        StateElem.update(self)
        if len(self.data)==0:
            self.data.append({})
        self.data[0]['creator']        = creator
        self.data[0]['owner']          = owner

class StateQueue(StateElem):
    
    def __init__(self):
        StateElem.__init__(self)
        
        for i in range(10):
            self.data.append(StateQueueRow())
    
    def update(self,notif):
        StateElem.update(self)
        self.data[0].update(notif.creator_0,notif.owner_0)
        self.data[1].update(notif.creator_1,notif.owner_1)
        self.data[2].update(notif.creator_2,notif.owner_2)
        self.data[3].update(notif.creator_3,notif.owner_3)
        self.data[4].update(notif.creator_4,notif.owner_4)
        self.data[5].update(notif.creator_5,notif.owner_5)
        self.data[6].update(notif.creator_6,notif.owner_6)
        self.data[7].update(notif.creator_7,notif.owner_7)
        self.data[8].update(notif.creator_8,notif.owner_8)
        self.data[9].update(notif.creator_9,notif.owner_9)

class StateNeighborsRow(StateElem):
    
    def update(self,notif):
        StateElem.update(self)
        if len(self.data)==0:
            self.data.append({})
        self.data[0]['used']           = notif.used
        self.data[0]['parentPreference']    = notif.parentPreference
        self.data[0]['stableNeighbor']      = notif.stableNeighbor
        self.data[0]['switchStabilityCounter']   = notif.switchStabilityCounter
        if 'addr' not in self.data[0]:
            self.data[0]['addr']   = typeAddr.typeAddr()
        self.data[0]['addr'].update(notif.addr_type,
                                    notif.addr_bodyH,
                                    notif.addr_bodyL)
        self.data[0]['DAGrank']        = notif.DAGrank
        self.data[0]['numRx']          = notif.numRx
        self.data[0]['numTx']          = notif.numTx
        self.data[0]['numTxACK']       = notif.numTxACK
        if 'asn' not in self.data[0]:
            self.data[0]['asn']        = typeAsn.typeAsn()
        self.data[0]['asn'].update(notif.asn_0_1,
                                   notif.asn_2_3,
                                   notif.asn_4)

class StateIsSync(StateElem):
    
    def update(self,notif):
        StateElem.update(self)
        if len(self.data)==0:
            self.data.append({})
        self.data[0]['isSync']         = notif.isSync

class StateIdManager(StateElem):
    
    def update(self,notif):
        StateElem.update(self)
        if len(self.data)==0:
            self.data.append({})
        self.data[0]['isDAGroot']      = notif.isDAGroot
        self.data[0]['isBridge']       = notif.isBridge
        if 'my16bID' not in self.data[0]:
            self.data[0]['my16bID']    = typeAddr.typeAddr()
        self.data[0]['my16bID'].update(notif.my16bID_type,
                                       notif.my16bID_bodyH,
                                       notif.my16bID_bodyL)
        if 'my64bID' not in self.data[0]:
            self.data[0]['my64bID']    = typeAddr.typeAddr()
        self.data[0]['my64bID'].update(notif.my64bID_type,
                                       notif.my64bID_bodyH,
                                       notif.my64bID_bodyL)
        if 'myPANID' not in self.data[0]:
            self.data[0]['myPANID']    = typeAddr.typeAddr()
        self.data[0]['myPANID'].update(notif.myPANID_type,
                                       notif.myPANID_bodyH,
                                       notif.myPANID_bodyL)
        if 'myPrefix' not in self.data[0]:
            self.data[0]['myPrefix']    = typeAddr.typeAddr()
        self.data[0]['myPrefix'].update(notif.myPrefix_type,
                                        notif.myPrefix_bodyH,
                                        notif.myPrefix_bodyL)

class StateMyDagRank(StateElem):
    
    def update(self,notif):
        StateElem.update(self)
        if len(self.data)==0:
            self.data.append({})
        self.data[0]['myDAGrank']      = notif.myDAGrank

class StateTable(StateElem):

    def __init__(self,rowClass):
        StateElem.__init__(self)
        self.meta[0]['rowClass']       = rowClass
        self.data                      = []

    def update(self,notif):
        StateElem.update(self)
        while len(self.data)<notif.row+1:
            self.data.append(self.meta[0]['rowClass']())
        self.data[notif.row].update(notif)

class moteState(MoteConnectorConsumer.MoteConnectorConsumer):
    
    ST_OUPUTBUFFER      = 'OutputBuffer'
    ST_ASN              = 'Asn'
    ST_MACSTATS         = 'MacStats'
    ST_SCHEDULEROW      = 'ScheduleRow'
    ST_SCHEDULE         = 'Schedule'
    ST_QUEUEROW         = 'QueueRow'
    ST_QUEUE            = 'Queue'
    ST_NEIGHBORSROW     = 'NeighborsRow'
    ST_NEIGHBORS        = 'Neighbors'
    ST_ISSYNC           = 'IsSync'
    ST_IDMANAGER        = 'IdManager'
    ST_MYDAGRANK        = 'MyDagRank'
    ALL_STATES          = [ST_OUPUTBUFFER,ST_ASN,ST_MACSTATS,ST_SCHEDULE,ST_QUEUE,ST_NEIGHBORS,ST_ISSYNC,ST_IDMANAGER,ST_MYDAGRANK]
    
    def __init__(self,moteConnector):
        
        # log
        log.debug("create instance")
        
        # store params
        self.moteConnector                  = moteConnector
        
        # initialize parent class
        MoteConnectorConsumer.MoteConnectorConsumer.__init__(self,self.moteConnector,
                                                                  [self.moteConnector.TYPE_STATUS],
                                                                  self._receivedData_notif)
        
        # local variables
        self.parserStatus                   = ParserStatus.ParserStatus()
        self.stateLock                      = threading.Lock()
        self.state                          = {}
        
        self.state[self.ST_OUPUTBUFFER]     = StateOutputBuffer()
        self.state[self.ST_ASN]             = StateAsn()
        self.state[self.ST_MACSTATS]        = StateMacStats()
        self.state[self.ST_SCHEDULE]        = StateTable(StateScheduleRow)
        self.state[self.ST_QUEUE]           = StateQueue()
        self.state[self.ST_NEIGHBORS]       = StateTable(StateNeighborsRow)
        self.state[self.ST_ISSYNC]          = StateIsSync()
        self.state[self.ST_IDMANAGER]       = StateIdManager()
        self.state[self.ST_MYDAGRANK]       = StateMyDagRank()
        
        self.notifHandlers = {
                self.parserStatus.named_tuple[self.ST_OUPUTBUFFER]:
                    self.state[self.ST_OUPUTBUFFER].update,
                self.parserStatus.named_tuple[self.ST_ASN]:
                    self.state[self.ST_ASN].update,
                self.parserStatus.named_tuple[self.ST_MACSTATS]:
                    self.state[self.ST_MACSTATS].update,
                self.parserStatus.named_tuple[self.ST_SCHEDULEROW]:
                    self.state[self.ST_SCHEDULE].update,
                self.parserStatus.named_tuple[self.ST_QUEUEROW]:
                    self.state[self.ST_QUEUE].update,
                self.parserStatus.named_tuple[self.ST_NEIGHBORSROW]:
                    self.state[self.ST_NEIGHBORS].update,
                self.parserStatus.named_tuple[self.ST_ISSYNC]:
                    self.state[self.ST_ISSYNC].update,
                self.parserStatus.named_tuple[self.ST_IDMANAGER]:
                    self.state[self.ST_IDMANAGER].update,
                self.parserStatus.named_tuple[self.ST_MYDAGRANK]:
                    self.state[self.ST_MYDAGRANK].update,
            }
    
    #======================== public ==========================================
    
    def getStateElem(self,elemName):
        
        if elemName not in self.state:
            raise ValueError('No state called {0}'.format(elemName))
        
        self.stateLock.acquire()
        returnVal = copy.deepcopy(self.state[elemName])
        self.stateLock.release()
        
        return returnVal
    
    def getStateElemNames(self):
        
        self.stateLock.acquire()
        returnVal = self.state.keys()
        self.stateLock.release()
        
        return returnVal
    
    #======================== private =========================================
    
    def _receivedData_notif(self,notif):
        
        # log
        log.debug("received {0}".format(notif))
        
        # lock the state data
        self.stateLock.acquire()
        
        # call handler
        found = False
        for k,v in self.notifHandlers.items():
            if self._isnamedtupleinstance(notif,k):
                found = True
                v(notif)
                break
        
        # unlock the state data
        self.stateLock.release()
        
        if found==False:
            raise SystemError("No handler for notif {0}".format(notif))
    
    def _isnamedtupleinstance(self,var,tupleInstance):
        return var._fields==tupleInstance._fields