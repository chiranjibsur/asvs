import vtk
from Bio import PDB

def load_pdb_to_vtk(file_path):
    """
    Loads a PDB file and converts it into a VTK Molecule object for rendering.
    Also prints summary information for verification.
    """
    parser = PDB.PDBParser(QUIET=True)
    structure = parser.get_structure("molecule", file_path)

    molecule = vtk.vtkMolecule()
    periodic_table = vtk.vtkPeriodicTable()  # For converting element symbols to atomic numbers
    atom_index_map = {}

    atom_count = 0
    bond_count = 0

    for model in structure:
        for chain in model:
            for residue in chain:
                for atom in residue:
                    element_symbol = atom.element.strip().capitalize()
                    atomic_number = periodic_table.GetAtomicNumber(element_symbol)

                    if atomic_number <= 0:
                        print(f"Warning: Unknown element '{element_symbol}', skipping atom.")
                        continue

                    atom_vtk_id = molecule.AppendAtom(atomic_number, *atom.coord)
                    atom_index_map[atom.serial_number] = atom_vtk_id
                    atom_count += 1

    # Add bonds (simple distance-based check)
    for model in structure:
        for chain in model:
            for residue in chain:
                atom_list = list(residue)
                for i, atom1 in enumerate(atom_list):
                    for j, atom2 in enumerate(atom_list[i + 1 :]):
                        if atom1 - atom2 < 1.6:
                            try:
                                molecule.AppendBond(
                                    atom_index_map[atom1.serial_number],
                                    atom_index_map[atom2.serial_number],
                                    1
                                )
                                bond_count += 1
                            except KeyError:
                                # In case atom was skipped due to unknown element
                                continue

    print(f"PDB Loaded from: {file_path}")
    print(f"Total atoms added: {atom_count}")
    print(f"Total bonds added: {bond_count}")

    return molecule

# Call function
mol = load_pdb_to_vtk(r"C:\Users\muska\Downloads\clean_project\static\examples\1cbs.pdb")
