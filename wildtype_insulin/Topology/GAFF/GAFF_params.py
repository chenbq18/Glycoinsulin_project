import os
import subprocess
from optparse import OptionParser
import parmed as pmd

# parsing user specified data
parser = OptionParser()
parser.add_option('-p', dest='pdb_file', help='Input .pdb file')
parser.add_option('-o', dest='output_name', help='String for names of output files')
parser.add_option('-m', dest='mdp_file', help='gromacs mdp file for energy evaluation')
parser.add_option('-n', dest='net_charge', help='net charge on molecule')
parser.add_option('--tinker', action='store_true',
                  help='Convert gromacs topolgy to Tinker .prm and determine energy differences')

(options, args) = parser.parse_args()
pdb_file = options.pdb_file
output_names = options.output_name
mdp_file = options.mdp_file
net_charge = options.net_charge

# Path to specific scripts
path = os.path.dirname(os.path.abspath(__file__))


# Converting pdb to mol2 file
subprocess.call(["antechamber", "-i ", pdb_file, "-fi", "pdb", "-o", pdb_file.split('.')[0] + ".mol2", "-fo", "mol2",
                 "-c", "bcc", "-s", "2"])
subprocess.call(["rm", "ANTECHAMBER_AC.AC", "ANTECHAMBER_AM1BCC.AC", "ANTECHAMBER_BOND_TYPE.AC", "ATOMTYPE.INF",
                 "ANTECHAMBER_AC.AC0", "ANTECHAMBER_AM1BCC_PRE.AC", "ANTECHAMBER_BOND_TYPE.AC0"])

# Determine parameters that amber does not have
subprocess.call(["parmchk", "-i", pdb_file.split('.')[0] + ".mol2", "-f", "mol2", "-o", output_names + ".frcmod"])

# Creating and running tleap to generate 
tleap_input = "source oldff/leaprc.ff99SB\nsource leaprc.gaff\nSUS = loadmol2 " + pdb_file.split('.')[0] + ".mol2\n" \
              "loadamberparams " + output_names + ".frcmod\nsaveoff SUS sus.lib\n" \
              "saveamberparm SUS " + output_names + ".prmtop " + output_names + ".inpcrd\nquit"
with open("tleap.in", "w") as f:
    f.write(tleap_input)
subprocess.call(["tleap", "-f", "tleap.in"])

# Using parmed to convert amber parameters to gromacs topology
amber_params = pmd.load_file(output_names + ".prmtop", output_names + ".inpcrd")
amber_params.save(output_names + "_amber.top")
amber_params.save(output_names + ".gro")

# Running a short gromacs simulation
subprocess.call(["gmx", "editconf", "-f", output_names + ".gro", "-o", "pre_run.gro", "-c", "-d", "3", "-bt", "cubic"])
subprocess.call(["gmx", "grompp", "-f", mdp_file, "-p", output_names + "_amber.top", "-c", "pre_run.gro", "-o", "run"])
subprocess.call(["gmx", "mdrun", "-v", "-deffnm", "run"])
subprocess.call(["gmx", "editconf", "-f", "run.gro", "-o", output_names + ".pdb"])

# Use OpenEye to assign partial charges
subprocess.call(["molcharge", "-in", output_names + ".pdb", "-out", output_names + ".mol2", "-method", "am1bccsym"])

# Replace the partial charges generated by antechamber with those created by molcharge
subprocess.call(["python", path + "/insertmol2charges.py", "-m", output_names + ".mol2", "-t",
                 output_names + "_amber.top", "-c", str(net_charge), "-o", output_names + "_amber.top"])

# Converting system to Tinker .prm file
if options.tinker == True:
    # Create the tinker .prm file from the gromacs .top file
    subprocess.call(["python", path + "/../Gro_to_Tink.py", "-t", output_names + "_amber.top", "-o",
                     output_names + "_amber", "-e", "amber"])


