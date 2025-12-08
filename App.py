import os
import vtk as vtk_module
from trame.app import get_server
from trame.widgets import html
from trame_vtklocal.widgets import vtklocal
from trame.ui.vuetify import SinglePageLayout
from Bio import PDB
from trame.widgets import upload

# Step 1: Load the PDB file and parse it with Biopython
def parse_pdb(pdb_file):
    # Initialize the PDB parser
    parser = PDB.PDBParser(QUIET=True)
    structure = parser.get_structure('Protein', pdb_file)
    
    # Extract atoms and bonds
    atoms = []
    bonds = []
    for model in structure:
        for chain in model:
            for residue in chain:
                for atom in residue:
                    atoms.append(atom)
                    # Create bonds based on atom connectivity
                    if atom.get_bonded_atoms():
                        for bonded_atom in atom.get_bonded_atoms():
                            bonds.append((atom, bonded_atom))
    return atoms, bonds

# Step 2: Create VTK representations for atoms and bonds
def create_vtk_representation(atoms, bonds):
    # Create a VTK renderer
    renderer = vtk_module.vtkRenderer()
    atoms_polydata = vtk_module.vtkPolyData()

    # Create VTK points and a list of atoms
    points = vtk_module.vtkPoints()
    for atom in atoms:
        points.InsertNextPoint(atom.coord)
    atoms_polydata.SetPoints(points)

    # Create VTK spheres for atoms
    atom_spheres = vtk_module.vtkGlyph3D()
    atom_spheres.SetSourceConnection(vtk_module.vtkSphereSource().GetOutputPort())
    atom_spheres.SetInputData(atoms_polydata)
    atom_spheres.Update()

    # Create bonds as lines between atoms
    bond_lines = vtk_module.vtkCellArray()
    for bond in bonds:
        atom1, atom2 = bond
        id1 = points.InsertNextPoint(atom1.coord)
        id2 = points.InsertNextPoint(atom2.coord)
        bond_lines.InsertNextCell(2)
        bond_lines.InsertCellPoint(id1)
        bond_lines.InsertCellPoint(id2)

    # Create VTK polydata for bonds
    bond_polydata = vtk_module.vtkPolyData()
    bond_polydata.SetPoints(points)
    bond_polydata.SetLines(bond_lines)

    # Visualize bonds as lines and atoms as spheres
    bond_mapper = vtk_module.vtkPolyDataMapper()
    bond_mapper.SetInputData(bond_polydata)
    bond_actor = vtk_module.vtkActor()
    bond_actor.SetMapper(bond_mapper)

    atom_mapper = vtk_module.vtkPolyDataMapper()
    atom_mapper.SetInputData(atom_spheres.GetOutput())
    atom_actor = vtk_module.vtkActor()
    atom_actor.SetMapper(atom_mapper)

    # Add actors to the renderer
    renderer.AddActor(bond_actor)
    renderer.AddActor(atom_actor)
    
    return renderer

# Step 3: Setup the Trame App with file upload
def main():
    # Set up the Trame server
    server = get_server()
    state, ctrl = server.state, server.controller
    
    # Create render window and renderer
    render_window = vtk_module.vtkRenderWindow()
    renderer = vtk_module.vtkRenderer()
    render_window.AddRenderer(renderer)
    renderer.SetBackground(0.1, 0.1, 0.2)

    # Upload handler
    def handle_file_upload(file_data, filename):
        if filename.endswith('.pdb'):
            # Save uploaded file temporarily
            temp_path = os.path.join('/tmp', filename)
            with open(temp_path, 'wb') as f:
                f.write(file_data)
            
            # Step 4: Parse the uploaded PDB file
            atoms, bonds = parse_pdb(temp_path)

            # Clear previous renderer
            renderer.RemoveAllViewProps()
            
            # Create the VTK actors
            atoms_polydata = vtk_module.vtkPolyData()
            points = vtk_module.vtkPoints()
            for atom in atoms:
                points.InsertNextPoint(atom.coord)
            atoms_polydata.SetPoints(points)

            # Create VTK spheres for atoms
            atom_spheres = vtk_module.vtkGlyph3D()
            sphere_source = vtk_module.vtkSphereSource()
            sphere_source.SetRadius(0.3)
            atom_spheres.SetSourceConnection(sphere_source.GetOutputPort())
            atom_spheres.SetInputData(atoms_polydata)
            atom_spheres.Update()

            atom_mapper = vtk_module.vtkPolyDataMapper()
            atom_mapper.SetInputConnection(atom_spheres.GetOutputPort())
            atom_actor = vtk_module.vtkActor()
            atom_actor.SetMapper(atom_mapper)
            renderer.AddActor(atom_actor)
            
            # Reset camera
            renderer.ResetCamera()
            render_window.Render()
            
            # Update view
            ctrl.view_update()
            
            state.status_message = f"Loaded {filename} with {len(atoms)} atoms"
        else:
            state.status_message = "Please upload a valid PDB file."

    # File upload widget
    @ctrl.add("upload_file")
    def on_upload(file_info):
        if file_info:
            handle_file_upload(file_info['content'], file_info['name'])

    # Layout with file upload widget and viewer
    with SinglePageLayout(server) as layout:
        layout.title.set_text("3D Molecular Visualization")
        
        with layout.toolbar:
            html.Div("Upload a PDB File for Visualization", classes="title")
        
        with layout.content:
            # Use trame-vtklocal for WASM-based rendering
            vtklocal.LocalView(
                render_window,
                ref="pdbView",
                namespace="pdbNS",
            )
        
        with layout.footer:
            html.Div("{{ status_message }}", classes="caption")

    # Run the server
    server.start()

if __name__ == '__main__':
    main()
