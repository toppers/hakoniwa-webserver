import struct
from typing import Optional


class DataPacket:
    def __init__(self, robot_name: str = '', channel_id: int = 0, body_data: Optional[bytes] = None):
        self.robot_name = robot_name
        self.channel_id = channel_id
        self.body_data = body_data or b''

    def get_channel_id(self) -> int:
        return self.channel_id

    def get_pdu_data(self) -> bytes:
        return self.body_data

    def get_robot_name(self) -> str:
        return self.robot_name

    @staticmethod
    def decode(data: bytes) -> 'DataPacket':
        if len(data) < 12:
            raise ValueError("データが短すぎます。")

        current_index = 0

        # ヘッダーの長さを取得
        header_length = struct.unpack_from('>i', data, current_index)[0]
        current_index += 4

        if len(data) < 4 + header_length:
            raise ValueError("指定されたヘッダー長が不正です。")

        # ロボット名の長さを取得
        robot_name_length = struct.unpack_from('>i', data, current_index)[0]
        current_index += 4

        # ロボット名を取得
        robot_name = data[current_index:current_index + robot_name_length].decode('utf-8')
        current_index += robot_name_length

        # チャネルIDを取得
        channel_id = struct.unpack_from('>i', data, current_index)[0]
        current_index += 4

        # ボディデータを取得
        body_data = data[current_index:]

        return DataPacket(robot_name=robot_name, channel_id=channel_id, body_data=body_data)

    def encode(self) -> bytes:
        robot_name_bytes = self.get_robot_name().encode('utf-8')
        robot_name_length = len(robot_name_bytes)

        # ヘッダーの長さを計算
        header_length = 4 + robot_name_length + 4 + len(self.get_pdu_data())
        total_length = 4 + header_length

        data = bytearray(total_length)
        current_index = 0

        # ヘッダー長
        struct.pack_into('>i', data, current_index, header_length)
        current_index += 4

        # ロボット名の長さ
        struct.pack_into('>i', data, current_index, robot_name_length)
        current_index += 4

        # ロボット名
        data[current_index:current_index + robot_name_length] = robot_name_bytes
        current_index += robot_name_length

        # チャネルID
        struct.pack_into('>i', data, current_index, self.get_channel_id())
        current_index += 4

        # ボディデータ
        if self.get_pdu_data():
            data[current_index:] = self.get_pdu_data()

        return bytes(data)
