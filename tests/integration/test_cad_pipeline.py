"""Integration tests for CAD pipeline: import -> mesh -> materials."""

from __future__ import annotations

import os
import sys
import tempfile
import pytest
import numpy as np

sys.path.insert(0, "/home/rid/Documents/Caad")

from src.cad.opencascade_wrapper import OpenCASCADEWrapper
from src.cad.cgal_meshing import CGALMeshing, Mesh
from src.cad.material_database import MaterialDatabase
from src.cad.boundary_conditions import BoundaryConditionManager
from src.cad.port_definition import PortDefinition


class TestCADImportAndMeshIntegration:
    """Test the full CAD import and meshing pipeline."""

    def test_step_import_and_mesh(self):
        """Verify STEP file can be imported and meshed successfully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a simple STEP file programmatically
            step_content = """
#DXFV260
#FILE_NAME(('test_cube.step'), ...);
#UNIT('length', PLANE_ANGLE_MEASURE_UNIT(), MASS_MEASURE_UNIT(), AREA_MEASURE_UNIT(), VOLUME_MEASURE_UNIT());
#AX2_PLC('axis2plc', #AXIS2_1, #DIR3_1);
#AXIS2_1('', '', #LOCAL_DIR_1, #LOCAL_DIR_2);
#DIR3_1('', (1.0, 0.0, 0.0));
#DIR3_2('', (0.0, 1.0, 0.0));
#LOCAL_DIR_1('', (0.0, 0.0, 1.0));
#LOCAL_DIR_2('', (-1.0, 0.0, 0.0));
#POLYLOOP('polyloop', [#VERTEX3_1, #VERTEX3_2, #VERTEX3_3]);
#VERTEX3_1('', #PNT3_1);
#VERTEX3_2('', #PNT3_2);
#VERTEX3_3('', #PNT3_3);
#PNT3_1('', #AX2_PLC, 0.0, 0.0);
#PNT3_2('', #AX2_PLC, 1.0, 0.0);
#PNT3_3('', #AX2_PLC, 0.0, 1.0);
ENDSEC;
END-ISO-10303-21;
"""
            step_path = os.path.join(tmpdir, "test.step")
            with open(step_path, "w") as f:
                f.write(step_content)

            # Import and validate
            wrapper = OpenCASCADEWrapper()
            shapes = wrapper.import_step_file(step_path)
            assert len(shapes) > 0, "Should import at least one shape"

            # Mesh the imported geometry
            mesh_gen = CGALMeshing()
            mesh = mesh_gen.generate_surface_mesh(shapes[0])
            assert mesh is not None, "Mesh generation should succeed"

    def test_material_database_integration(self):
        """Verify material database can be queried and combined."""
        db = MaterialDatabase()
        copper = db.get_material("copper")
        assert copper is not None
        assert hasattr(copper, "get_permittivity")

        # Test material combination
        composite = db.define_composite(["air", "copper"], volume_fractions=[0.5, 0.5])
        assert composite is not None


class TestPortDefinitionIntegration:
    """Test port definition with mesh and materials."""

    def test_port_on_mesh(self):
        """Verify ports can be defined on mesh surfaces."""
        # Create a simple mesh
        vertices = np.array([[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0]], dtype=np.float64)
        triangles = np.array([[0, 1, 2], [0, 2, 3]])

        # Define a port on the mesh
        port = PortDefinition(
            name="port_1",
            port_type="wave_port",
            position=np.array([0.5, 0.5, 0]),
            normal=np.array([0, 0, 1]),
        )

        assert port.name == "port_1"
        assert port.port_type == "wave_port"


class TestBoundaryConditionIntegration:
    """Test boundary conditions with materials and ports."""

    def test_bc_manager_with_materials(self):
        """Verify BC manager works with material database."""
        db = MaterialDatabase()
        bc_mgr = BoundaryConditionManager()

        # Add PEC boundary condition
        pec = bc_mgr.add_pec_boundary("outer_surface")
        assert pec is not None

        # Verify BC can reference materials
        copper = db.get_material("copper")
        if copper:
            pec.set_material(copper)


class TestFullCADPipeline:
    """End-to-end test for the CAD pipeline."""

    def test_import_mesh_setup_complete(self):
        """Verify full pipeline: import -> mesh -> materials -> BCs -> ports."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Step 1: Import geometry
            step_content = "#DXFV260\n#FILE_NAME(('test.step'), ());\nENDSEC;\nEND-ISO-10303-21;\n"
            step_path = os.path.join(tmpdir, "test.step")
            with open(step_path, "w") as f:
                f.write(step_content)

            wrapper = OpenCASCADEWrapper()
            shapes = wrapper.import_step_file(step_path)
            assert len(shapes) > 0

            # Step 2: Generate mesh
            mesh_gen = CGALMeshGenerator(target_edge_length=0.2)
            mesh = mesh_gen.generate_surface_mesh(shapes[0])
            assert mesh is not None

            # Step 3: Setup materials and BCs
            db = MaterialDatabase()
            bc_mgr = BoundaryConditionManager()
            bc_mgr.add_pec_boundary("outer")
            bc_mgr.add_radiation_boundary("far_field")

            # Step 4: Define ports
            port = PortDefinition(
                name="feed_port",
                port_type="lumped_port",
                position=np.array([0.5, 0.5, 0]),
                normal=np.array([0, 0, 1]),
            )
            assert port is not None
