Ramachandran plot using command ramplot

========================================================
This README documents the interpretation of ramplot output data

[x] there are 2d and 3d plots; the extra dimension in the 3d plot is frequency; what is frequency in this context? It is the frequency of the amino acid residue 
[x] there are 6 different ramachandran plots; preProline, cisPronline, transProline, Glycine, Valine-Isoleucine, and General;
[x] the pre in preProline is indicative spacially and not temporally; with nitrogen as the start terminal, ~~the residues before proline are distinct in their backbone angles, flexibility etc, since proline has a special structure: it has a ring structure that makes it unflexible, affecting perhaps the omega angle with the preceding residue;~~ proline is constrained due since its ring structure is with part of the backbone; this makes its presence on the plot deterministic, while other residues caught there due to other reasons; since preproline single handedly causes the rigidity, it is helpful to separate out these as their own data points to get a better look at the rest of the residues in that spot; if the preproline residue has weird angles, then it will show more prominently in the combined ramachandran plot since it is the only residue with those angles; not really; there are other residues that could have the same anlges, except for different reasons and we would want to nail down all the reasons that contribute to the structure of the protein; now, knowing preproline residue angles' reason to be those specific angles is helpful, but that is something already established, we are trying to look at the reasons for the rest of the residues geometry taking on the values they do;
    [x] proline has a ring in its backbone
        [x] why does having a ring in the backbone make it rigid? Due to the ring, it cannot bend like other residues that dont have steric hindrance; the restriction in mobility is in rotation: having a ring there means, now you have a point around which the entire molecule cannot rotate; there is also restriction in scissoring, twisting, and symmetric and antisymmetric stretching;
        [x] why does the ring in the backbone make the preceding molecule have a distinct geometry? the ring structure cause steric hindrance, causing the preceding molecule to adopt certain limiting conformation(s);
        [x] does the ring not affect the following residue? the following residue is linked to the C fo the Carbonyl, which is not part of the ring; 
    [x] valine and isoleucine get their own plot because of the branched structure (valine is branched at the beta carbon, isoleucine is branched at the beta and gamma carbons); the branched structure causes steric hindrance, which affects the geometry of the residue; this is why valine and isoleucine are grouped together in their own plot; 
    [x] glycine gets its own plot because it has no side chain, which means it has more flexibility in its backbone angles; this is why glycine is grouped separately;
    [x] why do cis-Proline and trans-Proline get their own, distinct plots? 
        [x] cis proline is different from trans proline, but they are not that different energetically, well not that different relative to other residues; trans proline still trumps cis proline in terms of abundance; cis proline because of its 0 degree omega angle,  would be more likely in a helical structure
        [x] due to the omega angle difference between cis and trans (wrt peptide bond with preceding residue) conformations, they form very different geometries with other residues; 
            [x] why would this affect phi and psi angles?  since different omega angles would affect the geometry of the residue, it would also affect the phi and psi angles;


    [x] which dihedral is phi and which is psi and which omega
        [x] phi is the dihedral angle about the N-Ca bond
        [x] psi is the dihedral angle about the Ca-C bond
        [x] omega is the dihedral angle about the C-N bond; it is usually 180 degrees, but it would be very different for proline for example; for trans proline which is more common, it is close to 180 degrees like for most other amino acids, cis or trans, but for cis proline, it is around 0 degrees;




d[] dont optimize before you standardize; standardize, then optimize; defining a relation: precedence of operation in the 'ought to' sense; a R b here would be a takes precedence over b in order of operation where order is defined temporally such that if a < b then a is done before b;  



[x] allowable vs favourable conformations in ramachandran plots
    [x] allowable conformations are represented by the dots within the outer contour
    [x] favourable conformations are represented by the dots within the inner contour

There are 6 types of 2d and 3d ramachandran plots: General, Gly, Val/Ile, prePro, transPro, cisPro

[] How do i interpret the 3d plots

There are a lot of disallowed conformations: look at the red dots in the 2d General+Gly single plot

Angles
Tau: 		N-C⍺-C angle 
Omega:	C-N (dihedral about the bond)
Phi:		N-Ca (dihedral about the bond)
Psi:		Ca-C (dihedral about the bond)
Chix:		sidechain dihedrals, 
Chi1:	N – Cα – Cβ – Cγ
Chi2: 	Cα – Cβ – Cγ – Cδ
And so on



[] Why were errors thrown for all 194 samples and only in calculating torsion angles
[] Although errors were thrown for all 194 samples, in the log file, there is some omega, psi and phi angles for some residues, but none with all three dihedral angles

[] What do I make of the energy ramachandran plots
[] interpret analysis.csv 
[] interpret ResultTorsionAngles.csv
