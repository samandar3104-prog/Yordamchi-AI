const express = require("express");
const axios = require("axios");
const app = express();
app.use(express.json());

const VERIFY_TOKEN = "instabot_secret_2024";
const CLAUDE_API_KEY = process.env.CLAUDE_API_KEY;
const IG_ACCESS_TOKEN = process.env.IG_ACCESS_TOKEN;

// Webhook verification
app.get("/webhook", (req, res) => {
  const mode = req.query["hub.mode"];
  const token = req.query["hub.verify_token"];
  const challenge = req.query["hub.challenge"];
  if (mode === "subscribe" && token === VERIFY_TOKEN) {
    console.log("Webhook verified!");
    res.status(200).send(challenge);
  } else {
    res.sendStatus(403);
  }
});

// Receive messages
app.post("/webhook", async (req, res) => {
  try {
    const body = req.body;
    if (body.object === "instagram") {
      for (const entry of body.entry) {
        for (const event of entry.messaging || []) {
          if (event.message && !event.message.is_echo) {
            const senderId = event.sender.id;
            const userMessage = event.message.text;
            console.log(`Message from ${senderId}: ${userMessage}`);
            const aiReply = await getAIReply(userMessage);
            await sendMessage(senderId, aiReply);
          }
        }
      }
    }
    res.sendStatus(200);
  } catch (err) {
    console.error(err);
    res.sendStatus(500);
  }
});

async function getAIReply(userMessage) {
  try {
    const response = await axios.post(
      "https://api.anthropic.com/v1/messages",
      {
        model: "claude-haiku-4-5-20251001",
        max_tokens: 300,
        system: process.env.AI_PROMPT || "Siz Instagram biznes akkaunt assistentidasiz. Savollarga qisqa, do'stona va professional javob bering.",
        messages: [{ role: "user", content: userMessage }],
      },
      {
        headers: {
          "x-api-key": CLAUDE_API_KEY,
          "anthropic-version": "2023-06-01",
          "content-type": "application/json",
        },
      }
    );
    return response.data.content[0].text;
  } catch (err) {
    console.error("Claude API error:", err.message);
    return "Hozir texnik muammo bor. Iltimos, keyinroq yozing.";
  }
}

async function sendMessage(recipientId, message) {
  try {
    await axios.post(
      `https://graph.instagram.com/v21.0/me/messages`,
      {
        recipient: { id: recipientId },
        message: { text: message },
      },
      {
        params: { access_token: IG_ACCESS_TOKEN },
      }
    );
    console.log(`Replied to ${recipientId}`);
  } catch (err) {
    console.error("Send message error:", err.message);
  }
}

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`InstaBot AI server running on port ${PORT}`);
});
