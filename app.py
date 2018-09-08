import asyncio
from quart import Quart, request
from utils.msgprocess import MessageProcess
from utils.tokens import VERIFY_TOKEN


app = Quart(__name__)

def verify_fb_token(token_sent):
    #take token sent by facebook and verify it matches the verify token you sent
    #if they match, allow the request, else return an error 
    if token_sent == VERIFY_TOKEN:
        return request.args.get("hub.challenge")
    return "Invalid verification token"

msg_instance = MessageProcess()

@app.route("/", methods=['GET', 'POST'])
async def receive_message():
    if request.method == 'GET':
        token_sent = request.args.get("hub.verify_token")
        return verify_fb_token(token_sent)
    else:
        output = await request.get_json()
        for event in output['entry']:
            messaging = event['messaging']
            for message in messaging:
                await msg_instance(message)
    return "Message Processed"
 
if __name__ == "__main__":
    app.run()