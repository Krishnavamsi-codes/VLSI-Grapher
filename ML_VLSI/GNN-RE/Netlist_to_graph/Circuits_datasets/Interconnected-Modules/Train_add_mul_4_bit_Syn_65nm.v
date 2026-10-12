/////////////////////////////////////////////////////////////
// Created by: Synopsys DC Ultra(TM) in wire load mode
// Version   : O-2018.06-SP5-5
// Date      : Fri Sep 25 09:53:24 2020
/////////////////////////////////////////////////////////////


module add_mul_4_bit ( a, b, operation, Result );
  input [0:3] a;
  input [0:3] b;
  output [0:7] Result;
  input operation;
  wire   \adder_1/n4 , \adder_1/n3 , \adder_1/n2 , \adder_1/n1 ,
         \multiplier_1/n63 , \multiplier_1/n62 , \multiplier_1/n61 ,
         \multiplier_1/n60 , \multiplier_1/n59 , \multiplier_1/n58 ,
         \multiplier_1/n57 , \multiplier_1/n56 , \multiplier_1/n55 ,
         \multiplier_1/n54 , \multiplier_1/n53 , \multiplier_1/n52 ,
         \multiplier_1/n51 , \multiplier_1/n50 , \multiplier_1/n49 ,
         \multiplier_1/n48 , \multiplier_1/n47 , \multiplier_1/n46 ,
         \multiplier_1/n45 , \multiplier_1/n44 , \multiplier_1/n43 ,
         \multiplier_1/n42 , \multiplier_1/n41 , \multiplier_1/n40 ,
         \multiplier_1/n39 , \multiplier_1/n38 , \multiplier_1/n37 ,
         \multiplier_1/n36 , \multiplier_1/n35 , \multiplier_1/n34 ,
         \multiplier_1/n33 , \multiplier_1/n32 , \multiplier_1/n31 ,
         \multiplier_1/n30 , \multiplier_1/n29 , \multiplier_1/n28 ,
         \multiplier_1/n27 , \multiplier_1/n26 , \multiplier_1/n25 ,
         \multiplier_1/n24 , \multiplier_1/n23 , \multiplier_1/n22 ,
         \multiplier_1/n21 , \multiplier_1/n20 , \multiplier_1/n19 ,
         \multiplier_1/n18 , \multiplier_1/n17 , \multiplier_1/n16 ,
         \multiplier_1/n15 , \multiplier_1/n14 , \multiplier_1/n13 ,
         \multiplier_1/n12 , \multiplier_1/n11 , \multiplier_1/n10 ,
         \multiplier_1/n9 , \multiplier_1/n8 , \multiplier_1/n7 ,
         \multiplier_1/n6 , \multiplier_1/n5 , \multiplier_1/n4 ,
         \multiplier_1/n3 , \multiplier_1/n2 , \multiplier_1/n1 ;
  wire   [0:7] Result_add;
  wire   [0:7] Result_mul;

  AND2_X0P5M_A9TH U9 ( .A(Result_mul[2]), .B(operation), .Y(Result[2]) );
  MX2_X0P5M_A9TH U10 ( .A(Result_add[4]), .B(Result_mul[4]), .S0(operation), 
        .Y(Result[4]) );
  MX2_X0P5M_A9TH U11 ( .A(Result_add[5]), .B(Result_mul[5]), .S0(operation), 
        .Y(Result[5]) );
  MX2_X0P5M_A9TH U12 ( .A(Result_add[6]), .B(Result_mul[6]), .S0(operation), 
        .Y(Result[6]) );
  MX2_X0P5M_A9TH U13 ( .A(Result_add[7]), .B(Result_mul[7]), .S0(operation), 
        .Y(Result[7]) );
  AND2_X0P5M_A9TH U14 ( .A(operation), .B(Result_mul[3]), .Y(Result[3]) );
  AND2_X0P5M_A9TH U15 ( .A(Result_mul[1]), .B(operation), .Y(Result[1]) );
  AND2_X0P5M_A9TH U16 ( .A(Result_mul[0]), .B(operation), .Y(Result[0]) );
  ADDF_X1M_A9TH \adder_1/U7  ( .A(b[1]), .B(a[1]), .CI(\adder_1/n4 ), .CO(
        \adder_1/n1 ), .S(Result_add[5]) );
  ADDF_X1M_A9TH \adder_1/U6  ( .A(b[2]), .B(a[2]), .CI(\adder_1/n3 ), .CO(
        \adder_1/n4 ), .S(Result_add[6]) );
  XOR3_X0P5M_A9TH \adder_1/U5  ( .A(\adder_1/n1 ), .B(b[0]), .C(a[0]), .Y(
        Result_add[4]) );
  NOR2_X0P5M_A9TH \adder_1/U4  ( .A(a[3]), .B(b[3]), .Y(\adder_1/n2 ) );
  AND2_X0P5M_A9TH \adder_1/U3  ( .A(a[3]), .B(b[3]), .Y(\adder_1/n3 ) );
  NOR2_X0P5M_A9TH \adder_1/U2  ( .A(\adder_1/n2 ), .B(\adder_1/n3 ), .Y(
        Result_add[7]) );
  INV_X0P5B_A9TH \multiplier_1/U65  ( .A(\multiplier_1/n57 ), .Y(
        \multiplier_1/n59 ) );
  OR2_X0P5M_A9TH \multiplier_1/U64  ( .A(\multiplier_1/n55 ), .B(
        \multiplier_1/n54 ), .Y(\multiplier_1/n56 ) );
  INV_X0P5B_A9TH \multiplier_1/U63  ( .A(\multiplier_1/n45 ), .Y(
        \multiplier_1/n47 ) );
  INV_X0P5B_A9TH \multiplier_1/U62  ( .A(\multiplier_1/n40 ), .Y(
        \multiplier_1/n42 ) );
  INV_X0P5B_A9TH \multiplier_1/U61  ( .A(\multiplier_1/n39 ), .Y(
        \multiplier_1/n48 ) );
  ADDF_X1M_A9TH \multiplier_1/U60  ( .A(\multiplier_1/n37 ), .B(
        \multiplier_1/n36 ), .CI(\multiplier_1/n35 ), .CO(\multiplier_1/n38 ), 
        .S(\multiplier_1/n29 ) );
  INV_X0P5B_A9TH \multiplier_1/U59  ( .A(\multiplier_1/n34 ), .Y(
        \multiplier_1/n50 ) );
  AOI21_X1M_A9TH \multiplier_1/U58  ( .A0(\multiplier_1/n31 ), .A1(
        \multiplier_1/n39 ), .B0(\multiplier_1/n30 ), .Y(\multiplier_1/n53 )
         );
  NAND2_X1M_A9TH \multiplier_1/U57  ( .A(\multiplier_1/n27 ), .B(
        \multiplier_1/n26 ), .Y(\multiplier_1/n46 ) );
  OAI21_X1M_A9TH \multiplier_1/U56  ( .A0(\multiplier_1/n25 ), .A1(
        \multiplier_1/n24 ), .B0(\multiplier_1/n23 ), .Y(\multiplier_1/n39 )
         );
  NOR2_X1A_A9TH \multiplier_1/U55  ( .A(\multiplier_1/n29 ), .B(
        \multiplier_1/n28 ), .Y(\multiplier_1/n40 ) );
  ADDF_X1M_A9TH \multiplier_1/U54  ( .A(\multiplier_1/n22 ), .B(
        \multiplier_1/n21 ), .CI(\multiplier_1/n20 ), .CO(\multiplier_1/n28 ), 
        .S(\multiplier_1/n27 ) );
  ADDH_X1M_A9TH \multiplier_1/U53  ( .A(\multiplier_1/n19 ), .B(
        \multiplier_1/n18 ), .CO(\multiplier_1/n35 ), .S(\multiplier_1/n20 )
         );
  NOR2_X1A_A9TH \multiplier_1/U52  ( .A(\multiplier_1/n17 ), .B(
        \multiplier_1/n32 ), .Y(\multiplier_1/n36 ) );
  NOR2_X1A_A9TH \multiplier_1/U51  ( .A(\multiplier_1/n33 ), .B(
        \multiplier_1/n16 ), .Y(\multiplier_1/n37 ) );
  NOR2_X1A_A9TH \multiplier_1/U50  ( .A(\multiplier_1/n27 ), .B(
        \multiplier_1/n26 ), .Y(\multiplier_1/n45 ) );
  ADDF_X1M_A9TH \multiplier_1/U49  ( .A(\multiplier_1/n15 ), .B(
        \multiplier_1/n14 ), .CI(\multiplier_1/n13 ), .CO(\multiplier_1/n26 ), 
        .S(\multiplier_1/n2 ) );
  NOR2_X1A_A9TH \multiplier_1/U48  ( .A(\multiplier_1/n33 ), .B(
        \multiplier_1/n12 ), .Y(\multiplier_1/n18 ) );
  NOR2_X1A_A9TH \multiplier_1/U47  ( .A(\multiplier_1/n11 ), .B(
        \multiplier_1/n32 ), .Y(\multiplier_1/n19 ) );
  ADDH_X1M_A9TH \multiplier_1/U46  ( .A(\multiplier_1/n10 ), .B(
        \multiplier_1/n9 ), .CO(\multiplier_1/n21 ), .S(\multiplier_1/n1 ) );
  ADDH_X1M_A9TH \multiplier_1/U45  ( .A(\multiplier_1/n5 ), .B(
        \multiplier_1/n4 ), .CO(\multiplier_1/n13 ), .S(\multiplier_1/n7 ) );
  INV_X0P5B_A9TH \multiplier_1/U44  ( .A(\multiplier_1/n25 ), .Y(
        \multiplier_1/n3 ) );
  NOR2_X1A_A9TH \multiplier_1/U43  ( .A(\multiplier_1/n2 ), .B(
        \multiplier_1/n1 ), .Y(\multiplier_1/n25 ) );
  NOR2_X1A_A9TH \multiplier_1/U42  ( .A(\multiplier_1/n17 ), .B(
        \multiplier_1/n12 ), .Y(\multiplier_1/n14 ) );
  NOR2_X1A_A9TH \multiplier_1/U41  ( .A(\multiplier_1/n33 ), .B(
        \multiplier_1/n62 ), .Y(\multiplier_1/n15 ) );
  XNOR2_X0P5M_A9TH \multiplier_1/U40  ( .A(\multiplier_1/n44 ), .B(
        \multiplier_1/n43 ), .Y(Result_mul[2]) );
  XOR2_X0P5M_A9TH \multiplier_1/U39  ( .A(\multiplier_1/n49 ), .B(
        \multiplier_1/n48 ), .Y(Result_mul[3]) );
  XOR2_X0P5M_A9TH \multiplier_1/U38  ( .A(\multiplier_1/n8 ), .B(
        \multiplier_1/n24 ), .Y(Result_mul[4]) );
  XOR2_X0P5M_A9TH \multiplier_1/U37  ( .A(\multiplier_1/n61 ), .B(
        \multiplier_1/n60 ), .Y(Result_mul[5]) );
  INV_X0P6M_A9TH \multiplier_1/U36  ( .A(b[3]), .Y(\multiplier_1/n63 ) );
  NOR2_X0P7A_A9TH \multiplier_1/U35  ( .A(\multiplier_1/n11 ), .B(
        \multiplier_1/n12 ), .Y(\multiplier_1/n5 ) );
  NAND2_X0P7M_A9TH \multiplier_1/U34  ( .A(\multiplier_1/n29 ), .B(
        \multiplier_1/n28 ), .Y(\multiplier_1/n41 ) );
  INV_X0P6M_A9TH \multiplier_1/U33  ( .A(\multiplier_1/n38 ), .Y(
        \multiplier_1/n51 ) );
  NAND2_X0P7M_A9TH \multiplier_1/U32  ( .A(\multiplier_1/n2 ), .B(
        \multiplier_1/n1 ), .Y(\multiplier_1/n23 ) );
  OAI21_X0P7M_A9TH \multiplier_1/U31  ( .A0(\multiplier_1/n46 ), .A1(
        \multiplier_1/n40 ), .B0(\multiplier_1/n41 ), .Y(\multiplier_1/n30 )
         );
  NAND2_X0P7M_A9TH \multiplier_1/U30  ( .A(\multiplier_1/n47 ), .B(
        \multiplier_1/n46 ), .Y(\multiplier_1/n49 ) );
  OAI21_X0P7M_A9TH \multiplier_1/U29  ( .A0(\multiplier_1/n53 ), .A1(
        \multiplier_1/n50 ), .B0(\multiplier_1/n51 ), .Y(Result_mul[0]) );
  XOR2_X0P5M_A9TH \multiplier_1/U28  ( .A(\multiplier_1/n53 ), .B(
        \multiplier_1/n52 ), .Y(Result_mul[1]) );
  INV_X0P7M_A9TH \multiplier_1/U27  ( .A(a[3]), .Y(\multiplier_1/n62 ) );
  INV_X0P7M_A9TH \multiplier_1/U26  ( .A(b[1]), .Y(\multiplier_1/n17 ) );
  INV_X0P7M_A9TH \multiplier_1/U25  ( .A(a[2]), .Y(\multiplier_1/n12 ) );
  INV_X0P7M_A9TH \multiplier_1/U24  ( .A(b[2]), .Y(\multiplier_1/n11 ) );
  INV_X0P7M_A9TH \multiplier_1/U23  ( .A(b[0]), .Y(\multiplier_1/n33 ) );
  INV_X0P7M_A9TH \multiplier_1/U22  ( .A(a[1]), .Y(\multiplier_1/n16 ) );
  INV_X0P7M_A9TH \multiplier_1/U21  ( .A(a[0]), .Y(\multiplier_1/n32 ) );
  NOR2_X0P5M_A9TH \multiplier_1/U20  ( .A(\multiplier_1/n17 ), .B(
        \multiplier_1/n16 ), .Y(\multiplier_1/n22 ) );
  NOR2_X0P5M_A9TH \multiplier_1/U19  ( .A(\multiplier_1/n11 ), .B(
        \multiplier_1/n62 ), .Y(\multiplier_1/n55 ) );
  NOR2_X0P5M_A9TH \multiplier_1/U18  ( .A(\multiplier_1/n11 ), .B(
        \multiplier_1/n16 ), .Y(\multiplier_1/n9 ) );
  NOR2_X0P5M_A9TH \multiplier_1/U17  ( .A(\multiplier_1/n63 ), .B(
        \multiplier_1/n16 ), .Y(\multiplier_1/n6 ) );
  NOR2_X0P5M_A9TH \multiplier_1/U16  ( .A(\multiplier_1/n33 ), .B(
        \multiplier_1/n32 ), .Y(\multiplier_1/n34 ) );
  NOR2_X0P5M_A9TH \multiplier_1/U15  ( .A(\multiplier_1/n63 ), .B(
        \multiplier_1/n32 ), .Y(\multiplier_1/n10 ) );
  NOR2_X0P5M_A9TH \multiplier_1/U14  ( .A(\multiplier_1/n63 ), .B(
        \multiplier_1/n62 ), .Y(Result_mul[7]) );
  NOR2_X0P7A_A9TH \multiplier_1/U13  ( .A(\multiplier_1/n17 ), .B(
        \multiplier_1/n62 ), .Y(\multiplier_1/n4 ) );
  NOR2_X0P5M_A9TH \multiplier_1/U12  ( .A(\multiplier_1/n63 ), .B(
        \multiplier_1/n12 ), .Y(\multiplier_1/n54 ) );
  NAND2_X0P5M_A9TH \multiplier_1/U11  ( .A(\multiplier_1/n55 ), .B(
        \multiplier_1/n54 ), .Y(\multiplier_1/n60 ) );
  NAND2_X0P5M_A9TH \multiplier_1/U10  ( .A(\multiplier_1/n7 ), .B(
        \multiplier_1/n6 ), .Y(\multiplier_1/n58 ) );
  AND2_X0P5M_A9TH \multiplier_1/U9  ( .A(\multiplier_1/n56 ), .B(
        \multiplier_1/n60 ), .Y(Result_mul[6]) );
  NOR2_X0P5M_A9TH \multiplier_1/U8  ( .A(\multiplier_1/n7 ), .B(
        \multiplier_1/n6 ), .Y(\multiplier_1/n57 ) );
  OA21_X0P5M_A9TH \multiplier_1/U7  ( .A0(\multiplier_1/n57 ), .A1(
        \multiplier_1/n60 ), .B0(\multiplier_1/n58 ), .Y(\multiplier_1/n24 )
         );
  NAND2_X0P5M_A9TH \multiplier_1/U6  ( .A(\multiplier_1/n59 ), .B(
        \multiplier_1/n58 ), .Y(\multiplier_1/n61 ) );
  NAND2_X0P7M_A9TH \multiplier_1/U5  ( .A(\multiplier_1/n34 ), .B(
        \multiplier_1/n51 ), .Y(\multiplier_1/n52 ) );
  NOR2_X0P5M_A9TH \multiplier_1/U4  ( .A(\multiplier_1/n45 ), .B(
        \multiplier_1/n40 ), .Y(\multiplier_1/n31 ) );
  NAND2_X0P7M_A9TH \multiplier_1/U3  ( .A(\multiplier_1/n42 ), .B(
        \multiplier_1/n41 ), .Y(\multiplier_1/n43 ) );
  NAND2_X0P5M_A9TH \multiplier_1/U2  ( .A(\multiplier_1/n3 ), .B(
        \multiplier_1/n23 ), .Y(\multiplier_1/n8 ) );
  OAI21_X0P7M_A9TH \multiplier_1/U1  ( .A0(\multiplier_1/n48 ), .A1(
        \multiplier_1/n45 ), .B0(\multiplier_1/n46 ), .Y(\multiplier_1/n44 )
         );
endmodule

