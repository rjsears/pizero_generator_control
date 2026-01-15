PiZero Generator Control Project
https://github.com/rjsears/pizero_generator_control

Overview:
The project is intended to control the starting and stoping of a generator
wirelessly. The system is designed with two raspberry PI Zero 2Ws. One will 
be the GenMaster and one will be GenSlave. The GenSlave is outfitted with
an "Automation Hat Mini" by Pimoroni

Information about the Automation Hat Mini can be found here:
https://shop.pimoroni.com/products/automation-hat-mini?variant=31478878077011

The necessary library files you will need to make it work can be found here:
https://github.com/pimoroni/automation-hat

On the GenMaster side there will be a two wire connection coming from a Victron
Cerbo GX MK2 relay one:

https://www.victronenergy.com/media/pg/Cerbo_GX/en/index-en.html

This two wire connection will be a "normally open" connection and will need
to be connected to GPIO  pins on the GenMaster. It will be connected to GPIO17
(Pin 11). When the Victron Cerbo decides to run the generator, it will close
that connection. We need to sense when that happens and When that happens, 
I need GenMaster to transmit a command via wifi to GenSlave to close the relay
on the Automation Hat mini. This will cause the generator to start up. When the
Victron Cerbo wants to shut down the generator, it will cause that connection to 
open and the Pi will sense that and when it down, it needs to send a command to
GenSlave to open its relay thereby shutting down the generator.

I want a very lightweight website to be running on the GenMaster that shows
if the generator has been commanded to run and if it is running, how long it has
been running. I also want to have a "health" meter showing that we are in constant
communication with GenSlave, so there needs to be some type of very lightweight
heartbeat bidirectionally between them. Each needs to know that the other is alive
and if they lose communication with each other, then it needs to call a webhook with
a failure message and if communication comes back it needs to call a webhook with an
"alive" message. There should also be a button to "test" the webhook communication as
well as a button to "Reboot" the Pi Zero. We should also be able to start the generator
manually and tell it how long to run. Anytime we do any of these things we need to have the
ability to call a webhook for notifications. 

I want it to be a very nice but very lightweight website, it will be running
python3, nginx, MarinaDB, and maybe we should use Vue.js and Tailwind, fastAPI, APScheduler,
SqlAlchemy, CHart.js, etc. So that we have a very cool looking web interface.
 
Review https://www.github.com/rjsears/n8n_nginx/test_branch
to see how I like my websites to look. 

Because we have a database, I would like to track generator start and stop times, total
generator run times, have the ability to schedule a generator run cycle, have the ability
to override the run command from the Victron with a little virtual switch and if that
little switch is pressed, then it needs to call a webhook with a "manual override activated" (basically a bypass operation),
and when the "switch" is put back, then it needs to call a webhook with an "Automatic Operation Enabled"
message. We can work on the exact layout of the webhook messages as we go as these will be 
webhooks on an n8n system. 

I want 100% of all state information read from and written to a database. That way, in case the
Pi reboots, when it reboots the first thing that it needs to do is to read its current state information
to see what it is supposed to be doing. If the state shows that we are supposed to be running AND the 
Victron has GPIO17 grounded, then we need to reach out to GenSlave and see if it is running. If it
is NOT running, then we need to issue the run command. Likewise, if we reboot and it shows that we
are supposed to be running, but the Victron does not say we should be running and we have not been
marked to have a "manual run", then we would not start the generator and we would want to reach out 
to GenSlave and make sure it was NOT running the generator. My guess is that GenSlave should have an
API of some sort (maybe both of them) via FastAPI so that it will be easier to control and manage this
entire system.

I want a 60 second bi-directional healthcheck between the two and we can write that to the database as well (not every one, just
the last one). If we lose communication with the other side, we need to call a webhook (lost comm) with
the name of the side that is reporting and when the communication was lost. We will have to work on 
the actual webhook call so that it works with our system. Please review the API from 
https://www.github.com/rjsears/n8n_nginx/test_branch to see if we can do it via an API call since we
will be using Tailscale and either device could call the notification API directly. Let's really look
at the best way to do that but assume that both devices have direct access to a fully running n8n_management
instance and that we can create whatever slugs are necessary to make the notificaiton system work. Maybe
write in the database the unixtime stamp of just the last health check and every 60 seconds look at it
again. If we fail 3 healthchecks in a row then we can put some failsafes in place. If GenMaster loses 
communication with GenSlave then a notification has to go out, we should manually override the generator
and put it into manual shutdown in the database if the victon is telling us to run we would not want to
send a run signal when we can't communicate. 

If GenSlave loses communication with GenMaster (lost communication is considered XX number of 1 minutes polls) and this
is configurable on the web interface of GenMaster and pushed to the database of GenSLave to read, then it would automatically
shut down the generator if it were running, sen

I'm thinking notifications for the following:
Lost Communication
Generator Started - Victron Commanded
Generator Started - Scheduled Manually
Generator Started - Manually
Generator Stopped - Victorn COmmanded
Generator Stopped - Manual Override
Generator Stopped - End of Manually Scheduled Run
Geneartor Stopped - Loss of Communication (this could only be sent by GenSlave)


On the heartbeat, figure out a very lightweight of keeping communication alive between
them, and it can't just be a ping. I am thinking hitting an API endpoint that resets a timer
or something, but it really needs to be fool proof as it can be with sfailsafes. I will want you to really think it
over with me and come up with good suggestions.

You will need to research on how to read GPIO pins via python and you will also need to read up on the 
automation Hat on how to control its relay. 
https://github.com/pimoroni/automation-hat

Boot Up process:

On boot up, the first thing that needs to be checked is to see if the GPIO17 is open. In most
cases this should be the case, and if it is and we have communication with GenSlave then we could check
with GenSlave to see if the generator is running (maybe we rebooted but we are still inside our comm timeout
window) and if it is, then we would be good to go. If the Victron says it should not be running and we
have not been manually configured to run (via switch or schedule) then it would command a shutdown.

The software ahs to be very very very good at keeping and checking state information so that we are never in 
a position where the generator is running when it should not be running or in a position where it is
supposed to be running but is not. The other things I want the website to show if the temperaturs
of each Pi, how mcuh ram and cpu is in use, how much drive space is in use and the health of the drives
as these are SSD cards and won't last forever. 

Now I want you to take all of this information and digest it, I know I am pretty scattered brained, but
read through it and ask any questions you have. I want to put together a very collaborative communication
and discussion on exactly we are going to do this given we are running on low power Pi Zero 2W, we need to keep
writes to the SSD cards low so we dont need log files and crap like that, everything we need should be in 
the database. We should have a "backup" button on the website that backs up the database and every bit of 
information we need will be there so if we have to rebuild the Pi with a new SSD we slip it in, clone the 
repo upload that database file and start the software and it will do a fully aotomatic recovery based on that
file. 

So lets start by you going through all of this documentations that I wrote and build a complete plan from start
to finish to cover every single topin I have touched on, break it out into intelligent sections so that we 
can cover each one, put down any questions that you have, come up with ideas on how best to implement
what I need done. Put all of that into a generator_project_outline.md file and push it to the repo and we can start talking
about it. 

With Pi will run Docker so maybe the best way would be to build a GenMaster container with everything in it
and a GenSlave container with everything in it so we don't have to reply on running everything directly on the
host itself. Take that into consideration and give me the pros and cons of doing that. If we decide to go that 
route, the setup script for each ./setup.sh --GenMaster of ./setup.sh --GenSlave will need to install all required
components that we will need outside of the container. 
