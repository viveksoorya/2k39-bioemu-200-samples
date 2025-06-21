// ----------------------------------------------------------------------------
// Render triangulated surfaces using OpenGL.
//
#ifndef SURFRENDERER_HEADER_INCLUDED
#define SURFRENDERER_HEADER_INCLUDED

#include <vector>		// use std::vector
#include <set>			// use std::set<>

#include "rcarray.h"		// use Array<>

namespace Surface_Display
{

// ----------------------------------------------------------------------------
// Render triangulated surfaces.
//
class Surface_Renderer
{
public:
  Surface_Renderer();
  virtual ~Surface_Renderer();

  //
  // Each piece has one color and display style.
  // The vertices array is N by 3 containing xyz coordinates.
  // The triangles array is M by 3 containing indices into the
  // vertices array defining triangles.
  //
  class Piece
    {
    public:
      Piece(const FArray &vertices, const IArray &triangles);
      virtual ~Piece();

      bool shown() const;
      void show(bool s);

      void geometry(FArray *vertices, IArray *triangles) const;
      virtual void set_geometry(const FArray &vertices,
				const IArray &triangles);
      int vertex_count() const;
      int triangle_count() const;

      const float *placement() const;
      virtual void set_placement(const float *placement);

      const FArray &normals();
      virtual void set_normals(const FArray &normals);

      enum Display_Style { Solid, Mesh, Dot };
      Display_Style display_style() const;	// Solid, Mesh or Dot
      void set_display_style(Display_Style style);

      //
      // For single color surface pieces.
      //
      void color(float rgba_ret[4]) const;
      void set_color(float rgba[4]);

      //
      // Vertex colors override the single color specification.
      // To return to a single color surface pass in an empty array.
      // The vertex_rgba array has size N by 4 for a surface of N vertices.
      //
      const FArray &vertex_colors() const;
      virtual void set_vertex_colors(const FArray &vertex_rgba);

      //
      // Coloring with a texture overrides vertex and single color mode.
      // The texture coordinates array has size N by D for a surface of
      // N vertices and a texture of dimension D.
      // The texture id is an OpenGL texture id.
      // The transparency setting determines if texture alpha is used.
      // The modulation color is useful for non-white luminance textures.
      // The border color is for values outside the texture bounds.
      //
      const FArray &texture_coordinates() const;
      virtual void set_texture_coordinates(const FArray &texture_coords);
      unsigned int texture_id() const;
      void set_texture_id(unsigned int tid);
      bool use_texture_transparency() const;
      void set_use_texture_transparency(bool transp);
      int texture_dimension() const;
      const float *texture_modulation_color() const;
      void set_texture_modulation_color(float rgba[4]);
      const float *texture_border_color() const;
      void set_texture_border_color(float rgba[4]);

      bool use_lighting() const;
      void set_use_lighting(bool use);

      bool two_sided_lighting() const;
      void set_two_sided_lighting(bool two_sided);

      float line_thickness() const;			// pixels.
      void set_line_thickness(float thickness);

      float dot_size() const;				// pixels.
      void set_dot_size(float size);

      //
      // Smooth lines means use anti-aliasing.  If the blend mode is
      // (1,1-alpha) and lines are transparent then anti-aliasing is not
      // used even if smooth lines are requested because (alpha,1-alpha)
      // blend mode is required for anti-aliasing.
      //
      bool smooth_lines() const;
      void set_smooth_lines(bool smooth);

      // TODO: Add smooth points for dot display.

      // Blend mode 1,1-a is the default.
      enum Blend_Mode { SRC_1_DST_1_MINUS_ALPHA, SRC_ALPHA_DST_1_MINUS_ALPHA };
      Blend_Mode transparency_blend_mode() const;
      void set_transparency_blend_mode(Blend_Mode);

      //
      // Can turn off display of individual triangles or mesh edges.
      // Triangle and edge mask is a one dimensional array with length equal
      // to number of triangles used.
      // Bits 0, 1, 2 control edges 0-1, 1-2, 2-0.
      // Bit 3 controls triangle display.
      // A hidden triangle hides the triangle's edges.
      //
      const IArray &triangle_and_edge_mask() const;
      virtual void set_triangle_and_edge_mask(const IArray &mask);
      virtual void set_edge_mask(const IArray &mask);

      //
      // Convenience method for setting displayed triangles.  A triangle is
      // shown if its 3 vertices are shown.  Edge display is not changed.
      // The mask array has the same length as the vertex array and
      // contains 1 for shown, 0 for hidden.
      //
      virtual void set_triangle_mask_from_vertex_mask(const IArray &mask);

      void masked_geometry(Display_Style style, FArray *vertices,
			   IArray *triangles_or_edges_or_dots);

      // Bounds for displayed part
      virtual bool bounding_box(float xyz_min[3], float xyz_max[3]) = 0;
      virtual bool bounding_sphere(float xyz_center[3], float *radius) = 0;

    protected:
      FArray vertices;		// N by 3 array holding xyz
      FArray vertex_normals;	// N by 3 array
      FArray vertex_rgba;	// N by 4 array holding RGBA
      FArray texture_coords;	// N by D array
      IArray triangles;		// M by 3 array of vertex indices
      IArray te_mask;		// length M, holding triangle/edge display bits
      IArray masked_triangles;	// M by 3 array, displayed triangles
      IArray masked_edges;	// M by 2 array, unique edges for mesh display
      IArray masked_dots;	// M by 1 array, unique vertices for dot display
      float *placement_matrix;	// 3 x 4 rotation and translation
      bool show_it;
      Display_Style style;	// Solid, Mesh or Dot
      float rgba[4];
      bool lit;
      bool light_2_sides;
      float linethickness;
      float dot_siz;
      bool smoothlines;
      Blend_Mode blend_mode;
      unsigned int tid;		// Texture id.
      bool transp_texture;
      float texture_modulation_rgba[4], texture_border_rgba[4];
    };

  Piece *add_piece(const FArray &vertices, const IArray &triangles);
  bool have_piece(Piece *piece) const;
  void remove_piece(Piece *piece);

  enum Piece_Properties {PP_TRIANGLES = 0x1, PP_LINES = 0x2, PP_DOTS = 0x4,
			 PP_OPAQUE = 0x8, PP_TRANSPARENT = 0x10,
			 PP_LIT = 0x20, PP_UNLIT = 0x40,
			 PP_SHOWN = 0x80, PP_UNSHOWN = 0x100,
			 PP_NO_TEXTURE = 0x200, PP_TEXTURE_1D = 0x400,
			 PP_TEXTURE_2D = 0x800, PP_TEXTURE_3D = 0x1000,
			 PP_TEXTURE = 0x1c00 };
  void draw_pieces(unsigned int show_only, bool depth_sort = false);
  typedef std::vector<Surface_Renderer::Piece *> Piece_List;
  int filter_pieces(unsigned int props, Piece_List *plist = NULL);
  void draw_geometry(Piece *g, bool lit = false);  // Used for highlighting

  // Bounds for displayed part
  bool bounding_box(float xyz_min[3], float xyz_max[3]);
  bool bounding_sphere(float xyz_center[3], float *radius);

  float pixel_scale_factor() const;
  void set_pixel_scale_factor(float f);

private:
  std::set<Piece *> pieces;
  float pixel_scale;

  void draw_depth_sorted(Piece_List &plist);
};

}	// end of namespace Surface_Display

#endif
