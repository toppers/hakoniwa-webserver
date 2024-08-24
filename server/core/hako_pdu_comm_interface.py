from abc import ABC, abstractmethod
import json

class HakoPduInfo:
    def __init__(self, pdu_type: str, pdu_name: str):
        self.pdu_type = pdu_type
        self.pdu_name = pdu_name

    def get_message_json(self, pdu_data_json: str):
        # `__raw` で終わるキーを削除
        keys_to_remove = [key for key in pdu_data_json if key.endswith("__raw")]
        for key in keys_to_remove:
            del pdu_data_json[key]

        message = {
            "pdu_info": {
                "pdu_type": self.pdu_type,
                "pdu_name": self.pdu_name
            },
            "pdu_data": pdu_data_json
        }
        #print(f"pdu_type: {self.pdu_type}")
        #print(f"pdu_name: {self.pdu_name}")
        #print(f"pdu_data_json: {pdu_data_json}")
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
