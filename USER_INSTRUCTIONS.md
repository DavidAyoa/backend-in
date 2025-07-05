All ideas should be taken from /documentations, /examples and /implementations.

The goal of this project is to build a server that abstracts livekit perfectly using the livekit agents python framework without exposing it to the client.

Clients would be able to connect to the server and register, login (authenticate themselves), create an agent that can have an initial prompt and also have conversational context prompts that can be used to change conversation context on any session.

Clients will also have the ability to switch between using voice or text during conversation and also configure agents response types if both voice and text or just one.

I have .env file in the project with correct details and always use the detail below for testing:
{
  "username": "subshur_tester",
  "email": "tester@subshur.com",
  "password": "helsinki77%$"
}