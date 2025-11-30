import os
import vtk
from trame.app import get_server
from trame.widgets import html
from trame.widgets.vtk import VtkRemoteView
from trame.ui.html import DivLayout
from Bio import PDB

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
    renderer = vtk.vtkRenderer()
    atoms_polydata = vtk.vtkPolyData()

    # Create VTK points and a list of atoms
    points = vtk.vtkPoints()
    for atom in atoms:
        points.InsertNextPoint(atom.coord)
    atoms_polydata.SetPoints(points)

    # Create VTK spheres for atoms
    atom_spheres = vtk.vtkGlyph3D()
    atom_spheres.SetSourceConnection(vtk.vtkSphereSource().GetOutputPort())
    atom_spheres.SetInputData(atoms_polydata)
    atom_spheres.Update()

    # Create bonds as lines between atoms
    bond_lines = vtk.vtkCellArray()
    for bond in bonds:
        atom1, atom2 = bond
        id1 = points.InsertNextPoint(atom1.coord)
        id2 = points.InsertNextPoint(atom2.coord)
        bond_lines.InsertNextCell(2)
        bond_lines.InsertCellPoint(id1)
        bond_lines.InsertCellPoint(id2)

    # Create VTK polydata for bonds
    bond_polydata = vtk.vtkPolyData()
    bond_polydata.SetPoints(points)
    bond_polydata.SetLines(bond_lines)

    # Visualize bonds as lines and atoms as spheres
    bond_mapper = vtk.vtkPolyDataMapper()
    bond_mapper.SetInputData(bond_polydata)
    bond_actor = vtk.vtkActor()
    bond_actor.SetMapper(bond_mapper)

    atom_mapper = vtk.vtkPolyDataMapper()
    atom_mapper.SetInputData(atom_spheres.GetOutput())
    atom_actor = vtk.vtkActor()
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
    
    # Create VTK render window
    render_window = vtk.vtkRenderWindow()
    renderer = vtk.vtkRenderer()
    render_window.AddRenderer(renderer)
    
    # File upload handler triggered from JavaScript
    @ctrl.trigger("process_file")
    def process_file(file_content, file_name):
        if file_name and file_name.endswith('.pdb'):
            # Parse the uploaded PDB file
            import tempfile
            import base64
            
            # Decode base64 content if needed
            if isinstance(file_content, str):
                file_content = base64.b64decode(file_content.split(',')[-1])
            
            with tempfile.NamedTemporaryFile(mode='wb', suffix='.pdb', delete=False) as f:
                f.write(file_content)
                temp_path = f.name
            
            atoms, bonds = parse_pdb(temp_path)
            os.unlink(temp_path)

            # Update the renderer with molecular structure
            new_renderer = create_vtk_representation(atoms, bonds)
            
            # Copy actors from new_renderer to main renderer
            renderer.RemoveAllViewProps()
            actors = new_renderer.GetActors()
            actors.InitTraversal()
            actor = actors.GetNextActor()
            while actor:
                renderer.AddActor(actor)
                actor = actors.GetNextActor()
            
            renderer.ResetCamera()
            ctrl.view_update()
        elif file_name:
            print("Please upload a valid PDB file.")

    # Layout with file upload widget
    with DivLayout(server) as layout:
        with html.Div(style="height: 100vh; display: flex; flex-direction: column;"):
            html.H1("Upload a PDB File for Visualization")
            html.Input(
                type="file",
                accept=".pdb",
                __events=["change"],
                change="""
                    const file = $event.target.files[0];
                    if (file) {
                        const reader = new FileReader();
                        reader.onload = (e) => {
                            trigger('process_file', [e.target.result, file.name]);
                        };
                        reader.readAsDataURL(file);
                    }
                """
            )
            with html.Div(style="flex: 1;"):
                view = VtkRemoteView(render_window)
                ctrl.view_update = view.update

    # Run the server
    server.start()

if __name__ == '__main__':
    main()
