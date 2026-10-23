# Case Study: Through the Tunnel (Pointr)

*The original case text, kept here for reference.*

## The problem

A driver is following turn-by-turn directions on their phone. The road enters a long tunnel, GPS fades out, and stays
unusable for a few minutes. The navigation app still has to show where the car is, call out an exit inside the tunnel at
the right moment, and recover cleanly when the car comes out.

How would you keep estimating the car's position while GPS is gone? You can use any sensor a modern smartphone has, GPS
included. Anything else you can reasonably assume is available is yours to research, use and justify.

## Your task

1. Propose an approach, or several, for estimating the car's position while GPS is unreliable.
2. Build a visual simulator: a road with a tunnel, one or more cars driving through it, and the sensor data the phone would
   record along the way. Show the true position next to your estimate.
3. Use the simulator to evaluate your approach. Tell us how well it works, where it breaks, and why.

Assume each tunnel has a single lane and is 500 m to 5 km long. Beyond that, you choose the tunnels, the driving
scenarios, which sensors to simulate and how realistically. These choices are part of what we look at. Where something is
unspecified, make a reasonable assumption and write it down.

## What to send us

- **Code:** a public repository or an archive, with a README that gets the simulator running.
- **Write-up:** a few pages covering your approach, your assumptions, what you simulated and how, your results, the
  limitations, and what you would do next with real devices.
- **AI usage:** a few lines on how you used AI tools, and where you had to correct or overrule them.
- **Optional:** a short screen recording of the simulator.

## Ground rules

- **Stack:** any language, framework and libraries. Web, desktop or notebook is your call.
- **AI tools:** welcome, and we expect you to use them. You own every line, so be ready to explain or change any part of it.
- **Data:** no real data is required. If you want to record traces with your own phone, go ahead.
- **Questions:** email us if something blocks you. The open-endedness is intentional, so we may answer with "your call".

## What happens next

If we move forward, we will set up a 45 to 60 minute call where you run the simulator and walk us through your reasoning.
Expect us to ask for new scenarios and parameter changes live, and to dig into the choices you made, including the ones an
AI agent made for you.
