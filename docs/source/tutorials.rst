Tutorials
=========


Half-Wave Dipole Simulation (Simple)
------------------------------------

This tutorial demonstrates a basic half-wave dipole simulation.

.. code-block:: python

   import numpy as np
   from src.core.workflow import SimulationWorkflow

   # Create workflow for 1 GHz dipole
   wf = SimulationWorkflow(
       frequency=1e9,
       solver_type="EFIE",
       mesh_size=0.05,
   )

   # Run simulation
   results = wf.run()


Microstrip Patch Antenna (Intermediate)
---------------------------------------

This tutorial covers a microstrip patch antenna simulation with substrate materials.

.. code-block:: python

   from src.core.workflow import SimulationWorkflow

   wf = SimulationWorkflow(
       frequency=2.4e9,
       solver_type="CFIE",
       mesh_size=0.025,
   )


Patch Antenna Array (Advanced)
------------------------------

This tutorial demonstrates a 2x2 patch antenna array with mutual coupling analysis.

.. code-block:: python

   from src.core.batch_processor import BatchProcessor

   # Create multiple array configurations
   workflows = []
   for spacing in [0.5, 0.75, 1.0]:
       wf = SimulationWorkflow(
           frequency=2.4e9,
           element_spacing=spacing,
           solver_type="CFIE",
       )
       workflows.append(wf)

   # Run batch processing
   processor = BatchProcessor(max_workers=2)
   results = processor.run_batch(workflows)

