from flask import Flask, request
import json
from MTLF import *
from AnLF import *
from Model import *
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from pythonmodule import MTLF, AnLF

# app = Flask(__name__)

# @app.route('/', methods=['GET', 'POST'])
# def parser():
#     data = {}
#     if request.method == 'POST':
#         data = request.json
#         print(data)

#         if str(data['nfService']) == 'training':
#             MTLF(model)
#             data["data"] = "training finish"
#         elif str(data['nfService']) == 'inference':
#             inference_result = AnLF.AnLF(model,int(data['data']))
#             data["data"] = str(inference_result)
#         else:
#             data['data'] = "None (Wrong)"

#         data['reqNFInstanceID'] = data['reqNFInstanceID'] + 'hi'
#         data['nfService'] = data['nfService'] + '(reply)'
#         data['reqTime'] = data['reqTime']

#     return json.dumps(data)


def analytics():
    data = {}
    json_param = json.loads(sys.argv[1])
    print(f"Received Handover Analytics Request for")
    print(f"target_ue: {json_param.get('TargetUe')}")
    print(f"target_time: {json_param.get('TargetTime')}")
    # if str(json_param.get('nfService')) == 'training':
    #     MTLF(model)
    #     data["data"] = "training finish"
    #     print("training")
    # elif str(json_param.get('nfService')) == 'inference':
    #     inference_result = AnLF.predict_ue_location(json_param.get('target_ue') ,json_param.get('target_time'))
    #     data["data"] = str(inference_result)
    #     print("analytics")
    # else:
    #     data['data'] = "None (Wrong)"
    result = AnLF.predict_ue_location(json_param.get('TargetUe'))# ,json_param.get('TargetTime'))
    # data["result"] = str(result)
    # print("analytics")
    return json.dumps(result)

if __name__ == '__main__':
    # app.run(port=9538)
    print(analytics())
    # random()

