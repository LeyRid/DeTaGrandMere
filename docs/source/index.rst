DeTaGrandMere Documentation
===========================

DeTaGrandMere is an open-source electromagnetic simulation software based on the Method of Moments (MoM). It provides a complete simulation pipeline from CAD geometry import through meshing, solver execution, and post-processing with visualization and data export.

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   installation
   quickstart
   api
   tutorials
   references/file_formats
   troubleshooting


Installation Guide
==================

System Requirements
-------------------

- Python 3.10 or later
- NumPy (numerical computing)
- h5py (HDF5 file support)
- Matplotlib (plotting)
- Optional: CGAL, OpenCASCADE, PyVista, VTK for advanced features


Installation Steps
------------------

.. code-block:: bash

   # Clone the repository
   git clone https://github.com/your-org/detagrandmere.git
   cd detagrandmere

   # Install in development mode
   pip install -e .

   # Install optional dependencies
   pip install pyvista vtk


Quick Start Tutorial
====================

Basic Dipole Simulation
-----------------------

.. code-block:: python

   from src.core.workflow import SimulationWorkflow

   # Create a workflow for a half-wave dipole
   workflow = SimulationWorkflow(
       frequency=1e9,
       solver_type="EFIE",
       mesh_size=0.05,
   )

   # Run the simulation
   results = workflow.run()

   print(f"Resonant frequency: {results['resonant_frequency']} Hz")
   print(f"Directivity: {results['directivity']} dBi")


Advanced Features
=================

Batch Processing
----------------

.. code-block:: python

   from src.core.batch_processor import BatchProcessor

   processor = BatchProcessor(max_workers=2)
   results = processor.run_batch(workflows=[wf1, wf2, wf3])


Data Export
-----------

.. code-block:: python

   from src.utils.data_io import HDF5Exporter

   exporter = HDF5Exporter(compression=True)
   exporter.export_fields(
       near_field=E_near,
       far_field=E_far,
       frequencies=freqs,
       output_file="results.h5",
   )


API Reference
=============

.. toctree::
   :maxdepth: 2

   api/core
   api/cad
   api/post_processing
   api/utils


Tutorials
=========

.. toctree::
   :maxdepth: 2

   tutorials/dipole
   tutorials/patch
   tutorials/array


References
==========

- File Format Specifications
- Configuration Schema
- Mathematical Background


Troubleshooting
===============

Common Issues
-------------

Import errors
~~~~~~~~~~~~~

If you see ``ModuleNotFoundError``, ensure all dependencies are installed:

.. code-block:: bash

   pip install numpy h5py matplotlib pyvista vtk


CGAL/OpenCASCADE not found
~~~~~~~~~~~~~~~~~~~~~~~~~~~

The CGAL and OpenCASCADE libraries are optional. If not installed, the software will use stub implementations for testing.


Performance Tips
----------------

- Use ``BatchProcessor(max_workers=N)`` for parallel simulations
- Enable HDF5 compression for large field datasets
- Reduce mesh size only where high accuracy is needed

