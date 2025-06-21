# -----------------------------------------------------------------------------
# Save and restore cages.
#
def save_cage_state(file):

    import cage
    if len(cage.cage_marker_sets()) == 0:
        return

    s = Cages_State()
    from SessionUtil import objecttree
    t = objecttree.instance_tree_to_basic_tree(s)

    file.write('\n')
    file.write('def restore_cages():\n')
    file.write(' cage_state = \\\n')
    objecttree.write_basic_tree(t, file, indent = '  ')
    file.write('\n')
    file.write(' from CageBuilder import session\n')
    file.write(' session.restore_cage_state(cage_state)\n')
    file.write('\n')
    file.write('try:\n')
    file.write('  restore_cages()\n')
    file.write('except:\n')
    file.write("  reportRestoreError('Error restoring cages')\n")
    file.write('\n')
  
# -----------------------------------------------------------------------------
#
def restore_cage_state(cage_basic_state):

    
  from SessionUtil.stateclasses import Model_State, Xform_State
  from Surface.session import Surface_Model_State, Surface_Piece_State

  classes = (Cages_State,)
  name_to_class = dict((c.__name__,c) for c in classes)

  from SessionUtil import objecttree
  s = objecttree.basic_tree_to_instance_tree(cage_basic_state, name_to_class)
  s.restore_state()

# -----------------------------------------------------------------------------
#
class Cages_State:

  version = 1
  
  state_attributes = ('version',)

  def restore_state(self):

      from SimpleSession import registerAfterModelsCB
      registerAfterModelsCB(self.restore_cages, None)

  def restore_cages(self):

      # Restore cages from already restored marker sets.
      import cage
      cage.cage_marker_sets()
