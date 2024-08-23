from abc import ABC, abstractmethod
import json

class HakoPduInfo:
    def __init__(self, pdu_type: str, pdu_name: str):
        self.pdu_type = pdu_type
        self.pdu_name = pdu_name

    def get_message_json(self, pdu_data_json: str):
        message = {
            "pdu_info": {
                "pdu_type": self.pdu_type,
                "pdu_name": self.pdu_name
            },
            "pdu_data": pdu_data_json
        }
        return message

    def get_message_str(self, pdu_data_json: str):
        message = self.get_message_json(pdu_data_json)
        return json.dumps(message)

class HakoPduCommInterface(ABC):
    @abstractmethod
    async def advertise_pdu(self, pdu_info: HakoPduInfo):
        pass
    @abstractmethod
    async def publish_pdu(self, pdu_info: HakoPduInfo, pdu_data_json: str):
        pass
