from abc import ABC, abstractmethod
from server.core.data_packet import DataPacket
import json

class HakoPduCommInterface(ABC):
    @abstractmethod
    async def publish_pdu(self, packet: DataPacket):
        pass
