## Running instructions

To run the model, run "python model.py" or "python3 model.py" from the terminal, depending in your version of python.

## Basic design of a model machine

We have chosen to represent each model machine as a process, with pipe connections between different machines. The class ModelMachine is a wrapper around this basic design.

## Design decisions along the way

Instead of using a dictionary from pid to pipe to store the connections,
we decided to make use of the spec assumption that there are only 3 
machines, and use a list of pipes where the list index corresponds to a 
particular machine.

Instead of using a class for a message, we decided to use a named tuple with two fields.

First we were using the python built in logging module to do the logging, but did not succeed in 
logging to separate files from all processes simultaneously. We then decided to simplify our 
approach and write to files directly which worked much better and resulted in more 
straightforward code.

We first had a send(...) and event(...) functions defined for the model machine, but decided to keep 
all actions centralized in one place within the run(...) function instead. This was possible due 
to the very small bodies of the send(...) and event(...) functions which were just 1-2 lines. Since 
the helper functions were so small, the helpers almost seemed more bulky. We may revisit this decision
during testing.

At first we had a receiver process per connection, but that seemed to be unreasonable for scaling.
We decided to have just one receiver process per machine, listening on all connections. While this 
means that messages cannot be "instantaneously" received from both machines (they are received in order), 
we don't get the exponential blow up of processes when scaling.

We decided to give each message an ID to keep track of exactly which messages have been received (and 
when) and which were still on the queue. 

We chose to keep an extra shared Queue between processes to keep track of the queue size, as the 
function qsize() did not work on the mac we tested this on (this is a common thing apparently).

## Discussion

**"Examine the logs, and discuss (in the lab book) the size of the jumps in the values for the logical clocks, drift in the values of the local logical clocks in the different machines (you can get a god’s eye view because of the system time), and the impact different timings on such things as gaps in the logical clock values and length of the message queue. Observations and reflections about the model and the results of running the model are more than welcome.

Once you have run this on three virtual machines that can vary their internal times by an order of magnitude, try running it with a smaller variation in the clock cycles and a smaller probability of the event being internal. What differences do those variations make? Add these observations to your lab notebook. Play around, and see if you can find something interesting."**

### Clock drift

We refer to local logical clock time as LLCT below. Queue length is 0 unless otherwise specified.

Trial 1:
Machine M2 (clock rate 6) had LLCT 358 after a minute (as opposed to the expected 360).
Machine M1 (clock rate 4) had LLCT 354 after a minute.
Machine M3 (clock rate 3) had LLCT 356 after a minute.

Trial 2:
Machine M2 (clock rate 4) had LLCT 240 after a minute (expected 240).
Machine M3 (clock rate 4) had LLCT 240 after a minute.
Machine M1 (clock rate 1) had LLCT 181 after a minute. Queue length 21.

Trial 3: 
Machine M3 (clock rate 6) had LLCT 358 after a minute (expected 360).
Machine M2 (clock rate 5) had LLCT 358 after a minute.
Machine M1 (clock rate 5) had LLCT 356 after a minute. 

Trial 4: 
Machine M2 (clock rate 6) had LLCT 358 after a minute (expected 360).
Machine M3 (clock rate 4) had LLCT 357 after a minute.
Machine M1 (clock rate 1) had LLCT 237 after a minute. Queue length 38. 

Trial 5:
Machine M3 (clock rate 6) had LLCT 357 after a minute (expected 360).
Machine M1 (clock rate 3) had LLCT 354 after a minute.
Machine M2 (clock rate 1) had LLCT 221 after a minute. Queue length 45.

Based on these trials, we conclude that the machine with the highest clock tick rate 
has the least clock drift (0-3 ticks). However, the machine with the lowest clock tick rate 
drifts the farthest (especially if the clock rate is below 3). We also notice that the 
queue length is large for these slower machines. We conclude that the machine with the 
lowest clock rate is not able to keep up with taking messages off the queue and updating 
the logical clock, hence the radical drift.

### Smaller variation in clock rates

We ran a trial with random clock rates between 1-3 instead of 1-6. 
Machine M3 (clock rate 3) had LLCT 180 after a minute (expected 180).
Machine M2 (clock rate 2) had LLCT 174 after a minute.
Machine M1 (clock rate 1) had LLCT 177 after a minute.

There is some clock drift but the gaps between the clocks of 
different machines (highest vs lowest clock rate) are not as large. 
Also, over the course of the minute, even though M1 had the lowest clock rate, 
it was able to process the network queue consistently, never reaching above 
3 messages in the queue at a time. We conclude that lower variation in clock 
rates allows the machines to catch up with each others' messages, and 
preventing the radical clock drift and queue backlog we saw in the previous 
trials.

### Smaller probability of internal event

We ran a trial with a lower, 40% chance of an internal event (rand 1-5 instead of 
1-10). 
Machine M1 (clock rate 6) had LLCT 358 after a minute (expected 360).
Machine M3 (clock rate 3) had LLCT 358 after a minute.
Machine M2 (clock rate 1) had LLCT 152 after a minute. Queue length 88.

In this trial, the machine with the highest clock rate had small drift as expected, 
but the machine with the lowest clock rate had an even more radical drift. 
The queue size was also much larger. We conclude that when there is a lower chance 
of an internal event, the machines with the higher clock rates are producing 
messages at higher rates and absolutely pummeling the machine with the lower clock rate.
The slow machine is not able to process all the messages in time and backlogs even quicker.

