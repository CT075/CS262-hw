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

## Discussion

**"Examine the logs, and discuss (in the lab book) the size of the jumps in the values for the logical clocks, drift in the values of the local logical clocks in the different machines (you can get a god’s eye view because of the system time), and the impact different timings on such things as gaps in the logical clock values and length of the message queue. Observations and reflections about the model and the results of running the model are more than welcome.

Once you have run this on three virtual machines that can vary their internal times by an order of magnitude, try running it with a smaller variation in the clock cycles and a smaller probability of the event being internal. What differences do those variations make? Add these observations to your lab notebook. Play around, and see if you can find something interesting."**