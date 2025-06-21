# -----------------------------------------------------------------------------
#
def show_biounit():
  import MultiScale
  MultiScale.show_biological_unit()
  from Accelerators.standard_accelerators import main_window_focus
  main_window_focus()
    
# -----------------------------------------------------------------------------
#
def select_contacts(distance):
  from MultiScale.nearby import select_contacts
  select_contacts(distance, load_atoms = False, displayed_only = True)
def select_contacts_3():
  select_contacts(3)
def select_contacts_5():
  select_contacts(5)

# -----------------------------------------------------------------------------
#
def select_sequence_copies():
  import MultiScale
  mm = MultiScale.multiscale_manager(create = False)
  if mm:
    mm.select_sequence_copies()

# -----------------------------------------------------------------------------
#
def color_surfaces_to_match_atoms():
  import MultiScale
  MultiScale.color_surfaces_to_match_atoms()

# -----------------------------------------------------------------------------
#
def set_selected_biomt():
  import MultiScale
  MultiScale.set_selected_biomt()
  
# -----------------------------------------------------------------------------
#
from Accelerators import add_accelerator
add_accelerator('bu', 'Show molecule biological unit using multiscale tool',
		show_biounit)
add_accelerator('c3', 'Find 3A contacts between selected and unselected atoms',
		select_contacts_3)
add_accelerator('c5', 'Find 5A contacts between selected and unselected atoms',
		select_contacts_5)
add_accelerator('xc', 'Extend multiscale selection to sequence copies',
		select_sequence_copies)
add_accelerator('c=', 'Color multiscale surfaces to match a chain atom',
		color_surfaces_to_match_atoms)
add_accelerator('mB', 'Set biomt matrices for selected multiscale chains',
                set_selected_biomt)
