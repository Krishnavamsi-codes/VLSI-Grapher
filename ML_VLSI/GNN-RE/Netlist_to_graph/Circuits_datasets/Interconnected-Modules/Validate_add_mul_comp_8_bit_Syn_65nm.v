/////////////////////////////////////////////////////////////
// Created by: Synopsys DC Ultra(TM) in wire load mode
// Version   : O-2018.06-SP5-5
// Date      : Sat Sep 26 22:56:17 2020
/////////////////////////////////////////////////////////////


module add_mul_comp_8_bit ( a, b, Result );
  input [0:7] a;
  input [0:7] b;
  output [0:15] Result;
  wire   A_greater_B, n1, \adder_1/n1 , \adder_1/intadd_0/n1 ,
         \adder_1/intadd_0/n2 , \adder_1/intadd_0/n3 , \adder_1/intadd_0/n4 ,
         \adder_1/intadd_0/n5 , \adder_1/intadd_0/n6 , \adder_1/intadd_0/CI ,
         \multiplier_1/n238 , \multiplier_1/n237 , \multiplier_1/n236 ,
         \multiplier_1/n235 , \multiplier_1/n234 , \multiplier_1/n233 ,
         \multiplier_1/n232 , \multiplier_1/n231 , \multiplier_1/n230 ,
         \multiplier_1/n229 , \multiplier_1/n228 , \multiplier_1/n227 ,
         \multiplier_1/n226 , \multiplier_1/n225 , \multiplier_1/n224 ,
         \multiplier_1/n223 , \multiplier_1/n222 , \multiplier_1/n221 ,
         \multiplier_1/n220 , \multiplier_1/n219 , \multiplier_1/n218 ,
         \multiplier_1/n217 , \multiplier_1/n216 , \multiplier_1/n215 ,
         \multiplier_1/n214 , \multiplier_1/n213 , \multiplier_1/n212 ,
         \multiplier_1/n211 , \multiplier_1/n210 , \multiplier_1/n209 ,
         \multiplier_1/n208 , \multiplier_1/n207 , \multiplier_1/n206 ,
         \multiplier_1/n205 , \multiplier_1/n204 , \multiplier_1/n203 ,
         \multiplier_1/n202 , \multiplier_1/n201 , \multiplier_1/n200 ,
         \multiplier_1/n199 , \multiplier_1/n198 , \multiplier_1/n197 ,
         \multiplier_1/n196 , \multiplier_1/n195 , \multiplier_1/n194 ,
         \multiplier_1/n193 , \multiplier_1/n192 , \multiplier_1/n191 ,
         \multiplier_1/n190 , \multiplier_1/n189 , \multiplier_1/n188 ,
         \multiplier_1/n187 , \multiplier_1/n186 , \multiplier_1/n185 ,
         \multiplier_1/n184 , \multiplier_1/n183 , \multiplier_1/n182 ,
         \multiplier_1/n181 , \multiplier_1/n180 , \multiplier_1/n179 ,
         \multiplier_1/n178 , \multiplier_1/n177 , \multiplier_1/n176 ,
         \multiplier_1/n175 , \multiplier_1/n174 , \multiplier_1/n173 ,
         \multiplier_1/n172 , \multiplier_1/n171 , \multiplier_1/n170 ,
         \multiplier_1/n169 , \multiplier_1/n168 , \multiplier_1/n167 ,
         \multiplier_1/n166 , \multiplier_1/n165 , \multiplier_1/n164 ,
         \multiplier_1/n163 , \multiplier_1/n162 , \multiplier_1/n161 ,
         \multiplier_1/n160 , \multiplier_1/n159 , \multiplier_1/n158 ,
         \multiplier_1/n157 , \multiplier_1/n156 , \multiplier_1/n155 ,
         \multiplier_1/n154 , \multiplier_1/n153 , \multiplier_1/n152 ,
         \multiplier_1/n151 , \multiplier_1/n150 , \multiplier_1/n149 ,
         \multiplier_1/n148 , \multiplier_1/n147 , \multiplier_1/n146 ,
         \multiplier_1/n145 , \multiplier_1/n144 , \multiplier_1/n143 ,
         \multiplier_1/n142 , \multiplier_1/n141 , \multiplier_1/n140 ,
         \multiplier_1/n139 , \multiplier_1/n138 , \multiplier_1/n137 ,
         \multiplier_1/n136 , \multiplier_1/n135 , \multiplier_1/n134 ,
         \multiplier_1/n133 , \multiplier_1/n132 , \multiplier_1/n131 ,
         \multiplier_1/n130 , \multiplier_1/n129 , \multiplier_1/n128 ,
         \multiplier_1/n127 , \multiplier_1/n126 , \multiplier_1/n125 ,
         \multiplier_1/n124 , \multiplier_1/n123 , \multiplier_1/n122 ,
         \multiplier_1/n121 , \multiplier_1/n120 , \multiplier_1/n119 ,
         \multiplier_1/n118 , \multiplier_1/n117 , \multiplier_1/n116 ,
         \multiplier_1/n115 , \multiplier_1/n114 , \multiplier_1/n113 ,
         \multiplier_1/n112 , \multiplier_1/n111 , \multiplier_1/n110 ,
         \multiplier_1/n109 , \multiplier_1/n108 , \multiplier_1/n107 ,
         \multiplier_1/n106 , \multiplier_1/n105 , \multiplier_1/n104 ,
         \multiplier_1/n103 , \multiplier_1/n102 , \multiplier_1/n101 ,
         \multiplier_1/n100 , \multiplier_1/n99 , \multiplier_1/n98 ,
         \multiplier_1/n97 , \multiplier_1/n96 , \multiplier_1/n95 ,
         \multiplier_1/n94 , \multiplier_1/n93 , \multiplier_1/n92 ,
         \multiplier_1/n91 , \multiplier_1/n90 , \multiplier_1/n89 ,
         \multiplier_1/n88 , \multiplier_1/n87 , \multiplier_1/n86 ,
         \multiplier_1/n85 , \multiplier_1/n84 , \multiplier_1/n83 ,
         \multiplier_1/n82 , \multiplier_1/n81 , \multiplier_1/n80 ,
         \multiplier_1/n79 , \multiplier_1/n78 , \multiplier_1/n77 ,
         \multiplier_1/n76 , \multiplier_1/n75 , \multiplier_1/n74 ,
         \multiplier_1/n73 , \multiplier_1/n72 , \multiplier_1/n71 ,
         \multiplier_1/n70 , \multiplier_1/n69 , \multiplier_1/n68 ,
         \multiplier_1/n67 , \multiplier_1/n66 , \multiplier_1/n65 ,
         \multiplier_1/n64 , \multiplier_1/n63 , \multiplier_1/n62 ,
         \multiplier_1/n61 , \multiplier_1/n60 , \multiplier_1/n59 ,
         \multiplier_1/n58 , \multiplier_1/n57 , \multiplier_1/n56 ,
         \multiplier_1/n55 , \multiplier_1/n54 , \multiplier_1/n53 ,
         \multiplier_1/n52 , \multiplier_1/n51 , \multiplier_1/n50 ,
         \multiplier_1/n49 , \multiplier_1/n48 , \multiplier_1/n47 ,
         \multiplier_1/n46 , \multiplier_1/n45 , \multiplier_1/n44 ,
         \multiplier_1/n43 , \multiplier_1/n42 , \multiplier_1/n41 ,
         \multiplier_1/n40 , \multiplier_1/n39 , \multiplier_1/n38 ,
         \multiplier_1/n37 , \multiplier_1/n36 , \multiplier_1/n35 ,
         \multiplier_1/n34 , \multiplier_1/n33 , \multiplier_1/n32 ,
         \multiplier_1/n31 , \multiplier_1/n30 , \multiplier_1/n29 ,
         \multiplier_1/n28 , \multiplier_1/n27 , \multiplier_1/n26 ,
         \multiplier_1/n25 , \multiplier_1/n24 , \multiplier_1/n23 ,
         \multiplier_1/n22 , \multiplier_1/n21 , \multiplier_1/n20 ,
         \multiplier_1/n19 , \multiplier_1/n18 , \multiplier_1/n17 ,
         \multiplier_1/n16 , \multiplier_1/n15 , \multiplier_1/n14 ,
         \multiplier_1/n13 , \multiplier_1/n12 , \multiplier_1/n11 ,
         \multiplier_1/n10 , \multiplier_1/n9 , \multiplier_1/n8 ,
         \multiplier_1/n7 , \multiplier_1/n6 , \multiplier_1/n5 ,
         \multiplier_1/n4 , \multiplier_1/n3 , \multiplier_1/n2 ,
         \multiplier_1/n1 , \comparator_1/n14 , \comparator_1/n13 ,
         \comparator_1/n12 , \comparator_1/n11 , \comparator_1/n10 ,
         \comparator_1/n9 , \comparator_1/n8 , \comparator_1/n7 ,
         \comparator_1/n6 , \comparator_1/n5 , \comparator_1/n4 ,
         \comparator_1/n3 , \comparator_1/n2 , \comparator_1/n1 ;
  wire   [0:15] Result_add;
  wire   [0:15] Result_mul;

  BUFH_X1M_A9TH U17 ( .A(A_greater_B), .Y(n1) );
  MX2_X0P5M_A9TH U18 ( .A(Result_add[10]), .B(Result_mul[10]), .S0(n1), .Y(
        Result[10]) );
  MX2_X0P5M_A9TH U19 ( .A(Result_add[14]), .B(Result_mul[14]), .S0(n1), .Y(
        Result[14]) );
  MX2_X0P5M_A9TH U20 ( .A(Result_add[9]), .B(Result_mul[9]), .S0(n1), .Y(
        Result[9]) );
  MX2_X0P5M_A9TH U21 ( .A(Result_add[15]), .B(Result_mul[15]), .S0(n1), .Y(
        Result[15]) );
  MX2_X0P5M_A9TH U22 ( .A(Result_add[13]), .B(Result_mul[13]), .S0(n1), .Y(
        Result[13]) );
  MX2_X0P5M_A9TH U23 ( .A(Result_add[12]), .B(Result_mul[12]), .S0(n1), .Y(
        Result[12]) );
  MX2_X0P5M_A9TH U24 ( .A(Result_add[8]), .B(Result_mul[8]), .S0(n1), .Y(
        Result[8]) );
  MX2_X0P5M_A9TH U25 ( .A(Result_add[11]), .B(Result_mul[11]), .S0(n1), .Y(
        Result[11]) );
  AND2_X0P5M_A9TH U26 ( .A(n1), .B(Result_mul[0]), .Y(Result[0]) );
  AND2_X0P5M_A9TH U27 ( .A(Result_mul[1]), .B(n1), .Y(Result[1]) );
  AND2_X0P5M_A9TH U28 ( .A(n1), .B(Result_mul[6]), .Y(Result[6]) );
  AND2_X0P5M_A9TH U29 ( .A(n1), .B(Result_mul[5]), .Y(Result[5]) );
  AND2_X0P5M_A9TH U30 ( .A(n1), .B(Result_mul[7]), .Y(Result[7]) );
  AND2_X0P5M_A9TH U31 ( .A(n1), .B(Result_mul[4]), .Y(Result[4]) );
  AND2_X0P5M_A9TH U32 ( .A(n1), .B(Result_mul[3]), .Y(Result[3]) );
  AND2_X0P5M_A9TH U33 ( .A(n1), .B(Result_mul[2]), .Y(Result[2]) );
  XOR3_X0P5M_A9TH \adder_1/U5  ( .A(\adder_1/intadd_0/n1 ), .B(b[0]), .C(a[0]), 
        .Y(Result_add[8]) );
  NOR2_X0P5M_A9TH \adder_1/U4  ( .A(a[7]), .B(b[7]), .Y(\adder_1/n1 ) );
  AND2_X0P5M_A9TH \adder_1/U3  ( .A(a[7]), .B(b[7]), .Y(\adder_1/intadd_0/CI )
         );
  NOR2_X0P5M_A9TH \adder_1/U2  ( .A(\adder_1/n1 ), .B(\adder_1/intadd_0/CI ), 
        .Y(Result_add[15]) );
  ADDF_X1M_A9TH \adder_1/intadd_0/U2  ( .A(b[1]), .B(a[1]), .CI(
        \adder_1/intadd_0/n2 ), .CO(\adder_1/intadd_0/n1 ), .S(Result_add[9])
         );
  ADDF_X1M_A9TH \adder_1/intadd_0/U3  ( .A(b[2]), .B(a[2]), .CI(
        \adder_1/intadd_0/n3 ), .CO(\adder_1/intadd_0/n2 ), .S(Result_add[10])
         );
  ADDF_X1M_A9TH \adder_1/intadd_0/U4  ( .A(b[3]), .B(a[3]), .CI(
        \adder_1/intadd_0/n4 ), .CO(\adder_1/intadd_0/n3 ), .S(Result_add[11])
         );
  ADDF_X1M_A9TH \adder_1/intadd_0/U5  ( .A(b[4]), .B(a[4]), .CI(
        \adder_1/intadd_0/n5 ), .CO(\adder_1/intadd_0/n4 ), .S(Result_add[12])
         );
  ADDF_X1M_A9TH \adder_1/intadd_0/U6  ( .A(b[5]), .B(a[5]), .CI(
        \adder_1/intadd_0/n6 ), .CO(\adder_1/intadd_0/n5 ), .S(Result_add[13])
         );
  ADDF_X1M_A9TH \adder_1/intadd_0/U7  ( .A(b[6]), .B(a[6]), .CI(
        \adder_1/intadd_0/CI ), .CO(\adder_1/intadd_0/n6 ), .S(Result_add[14])
         );
  OR2_X0P5M_A9TH \multiplier_1/U213  ( .A(\multiplier_1/n192 ), .B(
        \multiplier_1/n191 ), .Y(\multiplier_1/n194 ) );
  NAND2_X0P5M_A9TH \multiplier_1/U212  ( .A(\multiplier_1/n177 ), .B(
        \multiplier_1/n174 ), .Y(\multiplier_1/n173 ) );
  ADDF_X1M_A9TH \multiplier_1/U211  ( .A(\multiplier_1/n169 ), .B(
        \multiplier_1/n168 ), .CI(\multiplier_1/n167 ), .CO(
        \multiplier_1/n175 ), .S(\multiplier_1/n170 ) );
  ADDF_X1M_A9TH \multiplier_1/U210  ( .A(\multiplier_1/n166 ), .B(
        \multiplier_1/n165 ), .CI(\multiplier_1/n164 ), .CO(
        \multiplier_1/n171 ), .S(\multiplier_1/n161 ) );
  OR2_X0P5M_A9TH \multiplier_1/U209  ( .A(\multiplier_1/n162 ), .B(
        \multiplier_1/n161 ), .Y(\multiplier_1/n179 ) );
  ADDF_X1M_A9TH \multiplier_1/U208  ( .A(\multiplier_1/n160 ), .B(
        \multiplier_1/n159 ), .CI(\multiplier_1/n158 ), .CO(
        \multiplier_1/n164 ), .S(\multiplier_1/n150 ) );
  ADDF_X1M_A9TH \multiplier_1/U207  ( .A(\multiplier_1/n157 ), .B(
        \multiplier_1/n156 ), .CI(\multiplier_1/n155 ), .CO(
        \multiplier_1/n167 ), .S(\multiplier_1/n165 ) );
  ADDF_X1M_A9TH \multiplier_1/U206  ( .A(\multiplier_1/n154 ), .B(
        \multiplier_1/n153 ), .CI(\multiplier_1/n152 ), .CO(
        \multiplier_1/n166 ), .S(\multiplier_1/n158 ) );
  ADDF_X1M_A9TH \multiplier_1/U205  ( .A(\multiplier_1/n151 ), .B(
        \multiplier_1/n150 ), .CI(\multiplier_1/n149 ), .CO(
        \multiplier_1/n162 ), .S(\multiplier_1/n145 ) );
  OAI21_X1M_A9TH \multiplier_1/U204  ( .A0(\multiplier_1/n185 ), .A1(
        \multiplier_1/n148 ), .B0(\multiplier_1/n147 ), .Y(\multiplier_1/n181 ) );
  OR2_X0P5M_A9TH \multiplier_1/U203  ( .A(\multiplier_1/n145 ), .B(
        \multiplier_1/n144 ), .Y(\multiplier_1/n188 ) );
  ADDF_X1M_A9TH \multiplier_1/U202  ( .A(\multiplier_1/n141 ), .B(
        \multiplier_1/n140 ), .CI(\multiplier_1/n139 ), .CO(
        \multiplier_1/n144 ), .S(\multiplier_1/n143 ) );
  ADDF_X1M_A9TH \multiplier_1/U201  ( .A(\multiplier_1/n138 ), .B(
        \multiplier_1/n137 ), .CI(\multiplier_1/n136 ), .CO(
        \multiplier_1/n149 ), .S(\multiplier_1/n139 ) );
  ADDF_X1M_A9TH \multiplier_1/U200  ( .A(\multiplier_1/n129 ), .B(
        \multiplier_1/n128 ), .CI(\multiplier_1/n127 ), .CO(
        \multiplier_1/n159 ), .S(\multiplier_1/n137 ) );
  ADDF_X1M_A9TH \multiplier_1/U199  ( .A(\multiplier_1/n124 ), .B(
        \multiplier_1/n123 ), .CI(\multiplier_1/n122 ), .CO(
        \multiplier_1/n151 ), .S(\multiplier_1/n141 ) );
  OR2_X0P5M_A9TH \multiplier_1/U198  ( .A(\multiplier_1/n143 ), .B(
        \multiplier_1/n142 ), .Y(\multiplier_1/n196 ) );
  ADDF_X1M_A9TH \multiplier_1/U197  ( .A(\multiplier_1/n121 ), .B(
        \multiplier_1/n120 ), .CI(\multiplier_1/n119 ), .CO(
        \multiplier_1/n142 ), .S(\multiplier_1/n102 ) );
  ADDF_X1M_A9TH \multiplier_1/U196  ( .A(\multiplier_1/n118 ), .B(
        \multiplier_1/n117 ), .CI(\multiplier_1/n116 ), .CO(
        \multiplier_1/n136 ), .S(\multiplier_1/n121 ) );
  ADDF_X1M_A9TH \multiplier_1/U195  ( .A(\multiplier_1/n113 ), .B(
        \multiplier_1/n112 ), .CI(\multiplier_1/n111 ), .CO(
        \multiplier_1/n138 ), .S(\multiplier_1/n110 ) );
  ADDF_X1M_A9TH \multiplier_1/U194  ( .A(\multiplier_1/n110 ), .B(
        \multiplier_1/n109 ), .CI(\multiplier_1/n108 ), .CO(
        \multiplier_1/n140 ), .S(\multiplier_1/n119 ) );
  ADDF_X1M_A9TH \multiplier_1/U193  ( .A(\multiplier_1/n107 ), .B(
        \multiplier_1/n106 ), .CI(\multiplier_1/n105 ), .CO(
        \multiplier_1/n122 ), .S(\multiplier_1/n109 ) );
  ADDF_X1M_A9TH \multiplier_1/U192  ( .A(\multiplier_1/n96 ), .B(
        \multiplier_1/n95 ), .CI(\multiplier_1/n94 ), .CO(\multiplier_1/n97 ), 
        .S(\multiplier_1/n89 ) );
  ADDF_X1M_A9TH \multiplier_1/U191  ( .A(\multiplier_1/n93 ), .B(
        \multiplier_1/n92 ), .CI(\multiplier_1/n91 ), .CO(\multiplier_1/n99 ), 
        .S(\multiplier_1/n98 ) );
  OR2_X0P5M_A9TH \multiplier_1/U190  ( .A(\multiplier_1/n79 ), .B(
        \multiplier_1/n78 ), .Y(\multiplier_1/n234 ) );
  ADDH_X1M_A9TH \multiplier_1/U189  ( .A(\multiplier_1/n74 ), .B(
        \multiplier_1/n73 ), .CO(\multiplier_1/n68 ), .S(\multiplier_1/n79 )
         );
  OR2_X0P5M_A9TH \multiplier_1/U188  ( .A(\multiplier_1/n82 ), .B(
        \multiplier_1/n81 ), .Y(\multiplier_1/n230 ) );
  ADDH_X1M_A9TH \multiplier_1/U187  ( .A(\multiplier_1/n72 ), .B(
        \multiplier_1/n71 ), .CO(\multiplier_1/n64 ), .S(\multiplier_1/n81 )
         );
  ADDF_X1M_A9TH \multiplier_1/U186  ( .A(\multiplier_1/n70 ), .B(
        \multiplier_1/n69 ), .CI(\multiplier_1/n68 ), .CO(\multiplier_1/n62 ), 
        .S(\multiplier_1/n82 ) );
  ADDF_X1M_A9TH \multiplier_1/U185  ( .A(\multiplier_1/n67 ), .B(
        \multiplier_1/n66 ), .CI(\multiplier_1/n65 ), .CO(\multiplier_1/n58 ), 
        .S(\multiplier_1/n84 ) );
  ADDF_X1M_A9TH \multiplier_1/U184  ( .A(\multiplier_1/n64 ), .B(
        \multiplier_1/n63 ), .CI(\multiplier_1/n62 ), .CO(\multiplier_1/n86 ), 
        .S(\multiplier_1/n85 ) );
  ADDH_X1M_A9TH \multiplier_1/U183  ( .A(\multiplier_1/n60 ), .B(
        \multiplier_1/n59 ), .CO(\multiplier_1/n54 ), .S(\multiplier_1/n63 )
         );
  ADDF_X1M_A9TH \multiplier_1/U182  ( .A(\multiplier_1/n58 ), .B(
        \multiplier_1/n57 ), .CI(\multiplier_1/n56 ), .CO(\multiplier_1/n88 ), 
        .S(\multiplier_1/n87 ) );
  ADDF_X1M_A9TH \multiplier_1/U181  ( .A(\multiplier_1/n55 ), .B(
        \multiplier_1/n54 ), .CI(\multiplier_1/n53 ), .CO(\multiplier_1/n96 ), 
        .S(\multiplier_1/n56 ) );
  ADDF_X1M_A9TH \multiplier_1/U180  ( .A(\multiplier_1/n52 ), .B(
        \multiplier_1/n51 ), .CI(\multiplier_1/n50 ), .CO(\multiplier_1/n47 ), 
        .S(\multiplier_1/n57 ) );
  ADDF_X1M_A9TH \multiplier_1/U179  ( .A(\multiplier_1/n45 ), .B(
        \multiplier_1/n44 ), .CI(\multiplier_1/n43 ), .CO(\multiplier_1/n23 ), 
        .S(\multiplier_1/n95 ) );
  ADDH_X1M_A9TH \multiplier_1/U178  ( .A(\multiplier_1/n42 ), .B(
        \multiplier_1/n41 ), .CO(\multiplier_1/n43 ), .S(\multiplier_1/n53 )
         );
  ADDF_X1M_A9TH \multiplier_1/U177  ( .A(\multiplier_1/n40 ), .B(
        \multiplier_1/n39 ), .CI(\multiplier_1/n38 ), .CO(\multiplier_1/n101 ), 
        .S(\multiplier_1/n100 ) );
  ADDF_X1M_A9TH \multiplier_1/U176  ( .A(\multiplier_1/n37 ), .B(
        \multiplier_1/n36 ), .CI(\multiplier_1/n35 ), .CO(\multiplier_1/n108 ), 
        .S(\multiplier_1/n40 ) );
  ADDF_X1M_A9TH \multiplier_1/U175  ( .A(\multiplier_1/n34 ), .B(
        \multiplier_1/n33 ), .CI(\multiplier_1/n32 ), .CO(\multiplier_1/n120 ), 
        .S(\multiplier_1/n38 ) );
  ADDF_X1M_A9TH \multiplier_1/U174  ( .A(\multiplier_1/n31 ), .B(
        \multiplier_1/n30 ), .CI(\multiplier_1/n29 ), .CO(\multiplier_1/n116 ), 
        .S(\multiplier_1/n32 ) );
  ADDF_X1M_A9TH \multiplier_1/U173  ( .A(\multiplier_1/n28 ), .B(
        \multiplier_1/n27 ), .CI(\multiplier_1/n26 ), .CO(\multiplier_1/n117 ), 
        .S(\multiplier_1/n34 ) );
  ADDH_X1M_A9TH \multiplier_1/U172  ( .A(\multiplier_1/n25 ), .B(
        \multiplier_1/n24 ), .CO(\multiplier_1/n118 ), .S(\multiplier_1/n37 )
         );
  ADDF_X1M_A9TH \multiplier_1/U171  ( .A(\multiplier_1/n23 ), .B(
        \multiplier_1/n22 ), .CI(\multiplier_1/n21 ), .CO(\multiplier_1/n39 ), 
        .S(\multiplier_1/n91 ) );
  ADDH_X1M_A9TH \multiplier_1/U170  ( .A(\multiplier_1/n17 ), .B(
        \multiplier_1/n16 ), .CO(\multiplier_1/n12 ), .S(\multiplier_1/n46 )
         );
  NOR2_X1A_A9TH \multiplier_1/U169  ( .A(\multiplier_1/n61 ), .B(
        \multiplier_1/n114 ), .Y(\multiplier_1/n51 ) );
  NOR2_X1A_A9TH \multiplier_1/U168  ( .A(\multiplier_1/n135 ), .B(
        \multiplier_1/n237 ), .Y(\multiplier_1/n52 ) );
  ADDF_X1M_A9TH \multiplier_1/U167  ( .A(\multiplier_1/n15 ), .B(
        \multiplier_1/n14 ), .CI(\multiplier_1/n13 ), .CO(\multiplier_1/n10 ), 
        .S(\multiplier_1/n49 ) );
  ADDF_X1M_A9TH \multiplier_1/U166  ( .A(\multiplier_1/n12 ), .B(
        \multiplier_1/n11 ), .CI(\multiplier_1/n10 ), .CO(\multiplier_1/n33 ), 
        .S(\multiplier_1/n93 ) );
  ADDH_X1M_A9TH \multiplier_1/U165  ( .A(\multiplier_1/n9 ), .B(
        \multiplier_1/n8 ), .CO(\multiplier_1/n29 ), .S(\multiplier_1/n11 ) );
  NOR2_X1A_A9TH \multiplier_1/U164  ( .A(\multiplier_1/n61 ), .B(
        \multiplier_1/n130 ), .Y(\multiplier_1/n14 ) );
  ADDF_X1M_A9TH \multiplier_1/U163  ( .A(\multiplier_1/n7 ), .B(
        \multiplier_1/n6 ), .CI(\multiplier_1/n5 ), .CO(\multiplier_1/n36 ), 
        .S(\multiplier_1/n21 ) );
  ADDF_X1M_A9TH \multiplier_1/U162  ( .A(\multiplier_1/n4 ), .B(
        \multiplier_1/n3 ), .CI(\multiplier_1/n2 ), .CO(\multiplier_1/n35 ), 
        .S(\multiplier_1/n22 ) );
  INV_X0P5B_A9TH \multiplier_1/U161  ( .A(\multiplier_1/n215 ), .Y(
        \multiplier_1/n90 ) );
  INV_X0P5B_A9TH \multiplier_1/U160  ( .A(\multiplier_1/n187 ), .Y(
        \multiplier_1/n146 ) );
  OR2_X0P5M_A9TH \multiplier_1/U159  ( .A(\multiplier_1/n171 ), .B(
        \multiplier_1/n170 ), .Y(\multiplier_1/n1 ) );
  XOR2_X0P5M_A9TH \multiplier_1/U158  ( .A(\multiplier_1/n184 ), .B(
        \multiplier_1/n183 ), .Y(Result_mul[2]) );
  XNOR2_X0P5M_A9TH \multiplier_1/U157  ( .A(\multiplier_1/n181 ), .B(
        \multiplier_1/n180 ), .Y(Result_mul[3]) );
  AOI21_X0P7M_A9TH \multiplier_1/U156  ( .A0(\multiplier_1/n198 ), .A1(
        \multiplier_1/n196 ), .B0(\multiplier_1/n186 ), .Y(\multiplier_1/n190 ) );
  XOR2_X0P5M_A9TH \multiplier_1/U155  ( .A(\multiplier_1/n190 ), .B(
        \multiplier_1/n189 ), .Y(Result_mul[4]) );
  XNOR2_X0P5M_A9TH \multiplier_1/U154  ( .A(\multiplier_1/n198 ), .B(
        \multiplier_1/n197 ), .Y(Result_mul[5]) );
  XNOR2_X0P5M_A9TH \multiplier_1/U153  ( .A(\multiplier_1/n204 ), .B(
        \multiplier_1/n203 ), .Y(Result_mul[6]) );
  INV_X0P5B_A9TH \multiplier_1/U152  ( .A(\multiplier_1/n205 ), .Y(
        \multiplier_1/n207 ) );
  XOR2_X0P5M_A9TH \multiplier_1/U151  ( .A(\multiplier_1/n209 ), .B(
        \multiplier_1/n208 ), .Y(Result_mul[7]) );
  XOR2_X0P5M_A9TH \multiplier_1/U150  ( .A(\multiplier_1/n214 ), .B(
        \multiplier_1/n213 ), .Y(Result_mul[8]) );
  XNOR2_X0P5M_A9TH \multiplier_1/U149  ( .A(\multiplier_1/n218 ), .B(
        \multiplier_1/n217 ), .Y(Result_mul[9]) );
  INV_X0P5B_A9TH \multiplier_1/U148  ( .A(\multiplier_1/n219 ), .Y(
        \multiplier_1/n221 ) );
  XOR2_X0P5M_A9TH \multiplier_1/U147  ( .A(\multiplier_1/n223 ), .B(
        \multiplier_1/n222 ), .Y(Result_mul[10]) );
  INV_X0P5B_A9TH \multiplier_1/U146  ( .A(\multiplier_1/n224 ), .Y(
        \multiplier_1/n226 ) );
  XOR2_X0P5M_A9TH \multiplier_1/U145  ( .A(\multiplier_1/n228 ), .B(
        \multiplier_1/n227 ), .Y(Result_mul[11]) );
  XNOR2_X0P5M_A9TH \multiplier_1/U144  ( .A(\multiplier_1/n232 ), .B(
        \multiplier_1/n231 ), .Y(Result_mul[12]) );
  XNOR2_X0P5M_A9TH \multiplier_1/U143  ( .A(\multiplier_1/n236 ), .B(
        \multiplier_1/n235 ), .Y(Result_mul[13]) );
  INV_X0P5B_A9TH \multiplier_1/U142  ( .A(\multiplier_1/n46 ), .Y(
        \multiplier_1/n18 ) );
  NAND2_X1M_A9TH \multiplier_1/U141  ( .A(\multiplier_1/n172 ), .B(
        \multiplier_1/n182 ), .Y(\multiplier_1/n177 ) );
  INV_X0P5B_A9TH \multiplier_1/U140  ( .A(\multiplier_1/n178 ), .Y(
        \multiplier_1/n163 ) );
  AOI21_X0P7M_A9TH \multiplier_1/U139  ( .A0(\multiplier_1/n181 ), .A1(
        \multiplier_1/n179 ), .B0(\multiplier_1/n163 ), .Y(\multiplier_1/n184 ) );
  AOI21_X0P7M_A9TH \multiplier_1/U138  ( .A0(\multiplier_1/n186 ), .A1(
        \multiplier_1/n188 ), .B0(\multiplier_1/n146 ), .Y(\multiplier_1/n147 ) );
  INV_X0P5B_A9TH \multiplier_1/U137  ( .A(\multiplier_1/n185 ), .Y(
        \multiplier_1/n198 ) );
  INV_X0P5B_A9TH \multiplier_1/U136  ( .A(\multiplier_1/n199 ), .Y(
        \multiplier_1/n209 ) );
  INV_X0P5B_A9TH \multiplier_1/U135  ( .A(\multiplier_1/n200 ), .Y(
        \multiplier_1/n202 ) );
  AOI21_X0P7M_A9TH \multiplier_1/U134  ( .A0(\multiplier_1/n216 ), .A1(
        \multiplier_1/n217 ), .B0(\multiplier_1/n90 ), .Y(\multiplier_1/n214 )
         );
  INV_X0P5B_A9TH \multiplier_1/U133  ( .A(\multiplier_1/n210 ), .Y(
        \multiplier_1/n212 ) );
  INV_X0P5B_A9TH \multiplier_1/U132  ( .A(\multiplier_1/n229 ), .Y(
        \multiplier_1/n83 ) );
  AOI21_X0P7M_A9TH \multiplier_1/U131  ( .A0(\multiplier_1/n230 ), .A1(
        \multiplier_1/n231 ), .B0(\multiplier_1/n83 ), .Y(\multiplier_1/n227 )
         );
  INV_X0P5B_A9TH \multiplier_1/U130  ( .A(\multiplier_1/n233 ), .Y(
        \multiplier_1/n80 ) );
  INV_X0P5B_A9TH \multiplier_1/U129  ( .A(\multiplier_1/n195 ), .Y(
        \multiplier_1/n186 ) );
  OR2_X0P5M_A9TH \multiplier_1/U128  ( .A(\multiplier_1/n89 ), .B(
        \multiplier_1/n88 ), .Y(\multiplier_1/n216 ) );
  INV_X0P5B_A9TH \multiplier_1/U127  ( .A(\multiplier_1/n193 ), .Y(
        \multiplier_1/n235 ) );
  AOI21_X0P7M_A9TH \multiplier_1/U126  ( .A0(\multiplier_1/n104 ), .A1(
        \multiplier_1/n199 ), .B0(\multiplier_1/n103 ), .Y(\multiplier_1/n185 ) );
  INV_X0P6M_A9TH \multiplier_1/U125  ( .A(a[7]), .Y(\multiplier_1/n237 ) );
  INV_X0P6M_A9TH \multiplier_1/U124  ( .A(a[4]), .Y(\multiplier_1/n114 ) );
  INV_X0P6M_A9TH \multiplier_1/U123  ( .A(a[5]), .Y(\multiplier_1/n75 ) );
  INV_X0P6M_A9TH \multiplier_1/U122  ( .A(b[6]), .Y(\multiplier_1/n76 ) );
  INV_X0P6M_A9TH \multiplier_1/U121  ( .A(b[5]), .Y(\multiplier_1/n61 ) );
  INV_X0P6M_A9TH \multiplier_1/U120  ( .A(b[4]), .Y(\multiplier_1/n115 ) );
  INV_X0P6M_A9TH \multiplier_1/U119  ( .A(a[1]), .Y(\multiplier_1/n134 ) );
  INV_X0P6M_A9TH \multiplier_1/U118  ( .A(a[2]), .Y(\multiplier_1/n125 ) );
  INV_X0P6M_A9TH \multiplier_1/U117  ( .A(b[7]), .Y(\multiplier_1/n238 ) );
  INV_X0P6M_A9TH \multiplier_1/U116  ( .A(a[3]), .Y(\multiplier_1/n130 ) );
  INV_X0P6M_A9TH \multiplier_1/U115  ( .A(b[0]), .Y(\multiplier_1/n131 ) );
  INV_X0P6M_A9TH \multiplier_1/U114  ( .A(a[0]), .Y(\multiplier_1/n132 ) );
  INV_X0P6M_A9TH \multiplier_1/U113  ( .A(b[3]), .Y(\multiplier_1/n133 ) );
  INV_X0P6M_A9TH \multiplier_1/U112  ( .A(b[2]), .Y(\multiplier_1/n135 ) );
  INV_X0P6M_A9TH \multiplier_1/U111  ( .A(b[1]), .Y(\multiplier_1/n126 ) );
  INV_X0P6M_A9TH \multiplier_1/U110  ( .A(a[6]), .Y(\multiplier_1/n77 ) );
  NOR2_X0P7A_A9TH \multiplier_1/U109  ( .A(\multiplier_1/n238 ), .B(
        \multiplier_1/n134 ), .Y(\multiplier_1/n17 ) );
  NOR2_X0P7A_A9TH \multiplier_1/U108  ( .A(\multiplier_1/n76 ), .B(
        \multiplier_1/n125 ), .Y(\multiplier_1/n16 ) );
  NOR2_X0P7A_A9TH \multiplier_1/U107  ( .A(\multiplier_1/n126 ), .B(
        \multiplier_1/n237 ), .Y(\multiplier_1/n15 ) );
  NOR2_X0P7A_A9TH \multiplier_1/U106  ( .A(\multiplier_1/n131 ), .B(
        \multiplier_1/n237 ), .Y(\multiplier_1/n7 ) );
  NOR2_X0P7A_A9TH \multiplier_1/U105  ( .A(\multiplier_1/n61 ), .B(
        \multiplier_1/n125 ), .Y(\multiplier_1/n6 ) );
  XOR2_X0P5M_A9TH \multiplier_1/U104  ( .A(\multiplier_1/n47 ), .B(
        \multiplier_1/n46 ), .Y(\multiplier_1/n48 ) );
  XOR2_X0P5M_A9TH \multiplier_1/U103  ( .A(\multiplier_1/n49 ), .B(
        \multiplier_1/n48 ), .Y(\multiplier_1/n94 ) );
  XOR2_X0P5M_A9TH \multiplier_1/U102  ( .A(\multiplier_1/n175 ), .B(
        \multiplier_1/n174 ), .Y(\multiplier_1/n176 ) );
  NAND2_X0P7M_A9TH \multiplier_1/U101  ( .A(\multiplier_1/n87 ), .B(
        \multiplier_1/n86 ), .Y(\multiplier_1/n220 ) );
  NAND2_X0P7M_A9TH \multiplier_1/U100  ( .A(\multiplier_1/n100 ), .B(
        \multiplier_1/n99 ), .Y(\multiplier_1/n206 ) );
  OAI21_X0P7M_A9TH \multiplier_1/U99  ( .A0(\multiplier_1/n219 ), .A1(
        \multiplier_1/n222 ), .B0(\multiplier_1/n220 ), .Y(\multiplier_1/n217 ) );
  NAND2_X0P5M_A9TH \multiplier_1/U98  ( .A(\multiplier_1/n179 ), .B(
        \multiplier_1/n178 ), .Y(\multiplier_1/n180 ) );
  OAI21_X0P7M_A9TH \multiplier_1/U97  ( .A0(\multiplier_1/n214 ), .A1(
        \multiplier_1/n210 ), .B0(\multiplier_1/n211 ), .Y(\multiplier_1/n199 ) );
  NAND2XB_X0P7M_A9TH \multiplier_1/U96  ( .BN(\multiplier_1/n184 ), .A(
        \multiplier_1/n1 ), .Y(\multiplier_1/n172 ) );
  XOR2_X0P5M_A9TH \multiplier_1/U95  ( .A(\multiplier_1/n177 ), .B(
        \multiplier_1/n176 ), .Y(Result_mul[1]) );
  NOR2_X0P5M_A9TH \multiplier_1/U94  ( .A(\multiplier_1/n133 ), .B(
        \multiplier_1/n134 ), .Y(\multiplier_1/n127 ) );
  NOR2_X0P5M_A9TH \multiplier_1/U93  ( .A(\multiplier_1/n133 ), .B(
        \multiplier_1/n132 ), .Y(\multiplier_1/n153 ) );
  NOR2_X0P5M_A9TH \multiplier_1/U92  ( .A(\multiplier_1/n135 ), .B(
        \multiplier_1/n134 ), .Y(\multiplier_1/n152 ) );
  NOR2_X0P5M_A9TH \multiplier_1/U91  ( .A(\multiplier_1/n131 ), .B(
        \multiplier_1/n130 ), .Y(\multiplier_1/n154 ) );
  NOR2_X0P5M_A9TH \multiplier_1/U90  ( .A(\multiplier_1/n115 ), .B(
        \multiplier_1/n75 ), .Y(\multiplier_1/n50 ) );
  NOR2_X0P5M_A9TH \multiplier_1/U89  ( .A(\multiplier_1/n238 ), .B(
        \multiplier_1/n130 ), .Y(\multiplier_1/n60 ) );
  NOR2_X0P5M_A9TH \multiplier_1/U88  ( .A(\multiplier_1/n131 ), .B(
        \multiplier_1/n114 ), .Y(\multiplier_1/n129 ) );
  NOR2_X0P5M_A9TH \multiplier_1/U87  ( .A(\multiplier_1/n133 ), .B(
        \multiplier_1/n237 ), .Y(\multiplier_1/n67 ) );
  NOR2_X0P5M_A9TH \multiplier_1/U86  ( .A(\multiplier_1/n133 ), .B(
        \multiplier_1/n77 ), .Y(\multiplier_1/n55 ) );
  NOR2_X0P5M_A9TH \multiplier_1/U85  ( .A(\multiplier_1/n61 ), .B(
        \multiplier_1/n75 ), .Y(\multiplier_1/n66 ) );
  NOR2_X0P5M_A9TH \multiplier_1/U84  ( .A(\multiplier_1/n133 ), .B(
        \multiplier_1/n75 ), .Y(\multiplier_1/n45 ) );
  NOR2_X0P5M_A9TH \multiplier_1/U83  ( .A(\multiplier_1/n115 ), .B(
        \multiplier_1/n114 ), .Y(\multiplier_1/n44 ) );
  NOR2_X0P5M_A9TH \multiplier_1/U82  ( .A(\multiplier_1/n238 ), .B(
        \multiplier_1/n77 ), .Y(\multiplier_1/n191 ) );
  NOR2_X0P5M_A9TH \multiplier_1/U81  ( .A(\multiplier_1/n126 ), .B(
        \multiplier_1/n132 ), .Y(\multiplier_1/n168 ) );
  NOR2_X0P5M_A9TH \multiplier_1/U80  ( .A(\multiplier_1/n126 ), .B(
        \multiplier_1/n125 ), .Y(\multiplier_1/n160 ) );
  NOR2_X0P5M_A9TH \multiplier_1/U79  ( .A(\multiplier_1/n131 ), .B(
        \multiplier_1/n125 ), .Y(\multiplier_1/n157 ) );
  NOR2_X0P5M_A9TH \multiplier_1/U78  ( .A(\multiplier_1/n76 ), .B(
        \multiplier_1/n114 ), .Y(\multiplier_1/n59 ) );
  NOR2_X0P5M_A9TH \multiplier_1/U77  ( .A(\multiplier_1/n61 ), .B(
        \multiplier_1/n237 ), .Y(\multiplier_1/n73 ) );
  NOR2_X0P5M_A9TH \multiplier_1/U76  ( .A(\multiplier_1/n135 ), .B(
        \multiplier_1/n132 ), .Y(\multiplier_1/n156 ) );
  NOR2_X0P5M_A9TH \multiplier_1/U75  ( .A(\multiplier_1/n76 ), .B(
        \multiplier_1/n134 ), .Y(\multiplier_1/n8 ) );
  NOR2_X0P5M_A9TH \multiplier_1/U74  ( .A(\multiplier_1/n131 ), .B(
        \multiplier_1/n134 ), .Y(\multiplier_1/n169 ) );
  NOR2_X0P5M_A9TH \multiplier_1/U73  ( .A(\multiplier_1/n76 ), .B(
        \multiplier_1/n77 ), .Y(\multiplier_1/n74 ) );
  NOR2_X0P5M_A9TH \multiplier_1/U72  ( .A(\multiplier_1/n238 ), .B(
        \multiplier_1/n132 ), .Y(\multiplier_1/n9 ) );
  NOR2_X0P5M_A9TH \multiplier_1/U71  ( .A(\multiplier_1/n238 ), .B(
        \multiplier_1/n125 ), .Y(\multiplier_1/n42 ) );
  NOR2_X0P5M_A9TH \multiplier_1/U70  ( .A(\multiplier_1/n61 ), .B(
        \multiplier_1/n77 ), .Y(\multiplier_1/n69 ) );
  NOR2_X0P5M_A9TH \multiplier_1/U69  ( .A(\multiplier_1/n126 ), .B(
        \multiplier_1/n134 ), .Y(\multiplier_1/n155 ) );
  NOR2_X0P5M_A9TH \multiplier_1/U68  ( .A(\multiplier_1/n115 ), .B(
        \multiplier_1/n77 ), .Y(\multiplier_1/n65 ) );
  NOR2_X0P5M_A9TH \multiplier_1/U67  ( .A(\multiplier_1/n135 ), .B(
        \multiplier_1/n114 ), .Y(\multiplier_1/n30 ) );
  NOR2_X0P5M_A9TH \multiplier_1/U66  ( .A(\multiplier_1/n115 ), .B(
        \multiplier_1/n237 ), .Y(\multiplier_1/n70 ) );
  NOR2_X0P5M_A9TH \multiplier_1/U65  ( .A(\multiplier_1/n115 ), .B(
        \multiplier_1/n132 ), .Y(\multiplier_1/n128 ) );
  NOR2_X0P5M_A9TH \multiplier_1/U64  ( .A(\multiplier_1/n126 ), .B(
        \multiplier_1/n75 ), .Y(\multiplier_1/n31 ) );
  NOR2_X0P5M_A9TH \multiplier_1/U63  ( .A(\multiplier_1/n76 ), .B(
        \multiplier_1/n75 ), .Y(\multiplier_1/n71 ) );
  NOR2_X0P5M_A9TH \multiplier_1/U62  ( .A(\multiplier_1/n131 ), .B(
        \multiplier_1/n132 ), .Y(\multiplier_1/n174 ) );
  NOR2_X0P5M_A9TH \multiplier_1/U61  ( .A(\multiplier_1/n76 ), .B(
        \multiplier_1/n237 ), .Y(\multiplier_1/n192 ) );
  NOR2_X0P5M_A9TH \multiplier_1/U60  ( .A(\multiplier_1/n238 ), .B(
        \multiplier_1/n114 ), .Y(\multiplier_1/n72 ) );
  NOR2_X0P5M_A9TH \multiplier_1/U59  ( .A(\multiplier_1/n238 ), .B(
        \multiplier_1/n75 ), .Y(\multiplier_1/n78 ) );
  NOR2_X0P5M_A9TH \multiplier_1/U58  ( .A(\multiplier_1/n131 ), .B(
        \multiplier_1/n77 ), .Y(\multiplier_1/n26 ) );
  NOR2_X0P5M_A9TH \multiplier_1/U57  ( .A(\multiplier_1/n76 ), .B(
        \multiplier_1/n130 ), .Y(\multiplier_1/n41 ) );
  NOR2_X0P5M_A9TH \multiplier_1/U56  ( .A(\multiplier_1/n133 ), .B(
        \multiplier_1/n114 ), .Y(\multiplier_1/n3 ) );
  NOR2_X0P5M_A9TH \multiplier_1/U55  ( .A(\multiplier_1/n238 ), .B(
        \multiplier_1/n237 ), .Y(Result_mul[15]) );
  NOR2_X0P5M_A9TH \multiplier_1/U54  ( .A(\multiplier_1/n115 ), .B(
        \multiplier_1/n134 ), .Y(\multiplier_1/n105 ) );
  NOR2_X0P5M_A9TH \multiplier_1/U53  ( .A(\multiplier_1/n115 ), .B(
        \multiplier_1/n125 ), .Y(\multiplier_1/n27 ) );
  NOR2_X0P5M_A9TH \multiplier_1/U52  ( .A(\multiplier_1/n133 ), .B(
        \multiplier_1/n125 ), .Y(\multiplier_1/n112 ) );
  NOR2_X0P5M_A9TH \multiplier_1/U51  ( .A(\multiplier_1/n61 ), .B(
        \multiplier_1/n134 ), .Y(\multiplier_1/n24 ) );
  NOR2_X0P5M_A9TH \multiplier_1/U50  ( .A(\multiplier_1/n61 ), .B(
        \multiplier_1/n132 ), .Y(\multiplier_1/n106 ) );
  NOR2_X0P5M_A9TH \multiplier_1/U49  ( .A(\multiplier_1/n135 ), .B(
        \multiplier_1/n77 ), .Y(\multiplier_1/n13 ) );
  NOR2_X0P5M_A9TH \multiplier_1/U48  ( .A(\multiplier_1/n115 ), .B(
        \multiplier_1/n130 ), .Y(\multiplier_1/n4 ) );
  NOR2_X0P5M_A9TH \multiplier_1/U47  ( .A(\multiplier_1/n131 ), .B(
        \multiplier_1/n75 ), .Y(\multiplier_1/n107 ) );
  NOR2_X0P5M_A9TH \multiplier_1/U46  ( .A(\multiplier_1/n126 ), .B(
        \multiplier_1/n130 ), .Y(\multiplier_1/n124 ) );
  NOR2_X0P5M_A9TH \multiplier_1/U45  ( .A(\multiplier_1/n135 ), .B(
        \multiplier_1/n75 ), .Y(\multiplier_1/n2 ) );
  NOR2_X0P5M_A9TH \multiplier_1/U44  ( .A(\multiplier_1/n133 ), .B(
        \multiplier_1/n130 ), .Y(\multiplier_1/n28 ) );
  NOR2_X0P5M_A9TH \multiplier_1/U43  ( .A(\multiplier_1/n126 ), .B(
        \multiplier_1/n114 ), .Y(\multiplier_1/n113 ) );
  NOR2_X0P5M_A9TH \multiplier_1/U42  ( .A(\multiplier_1/n135 ), .B(
        \multiplier_1/n125 ), .Y(\multiplier_1/n123 ) );
  NOR2_X0P5M_A9TH \multiplier_1/U41  ( .A(\multiplier_1/n126 ), .B(
        \multiplier_1/n77 ), .Y(\multiplier_1/n5 ) );
  NOR2_X0P5M_A9TH \multiplier_1/U40  ( .A(\multiplier_1/n135 ), .B(
        \multiplier_1/n130 ), .Y(\multiplier_1/n111 ) );
  NOR2_X0P5M_A9TH \multiplier_1/U39  ( .A(\multiplier_1/n76 ), .B(
        \multiplier_1/n132 ), .Y(\multiplier_1/n25 ) );
  NAND2_X0P5M_A9TH \multiplier_1/U38  ( .A(\multiplier_1/n192 ), .B(
        \multiplier_1/n191 ), .Y(\multiplier_1/n193 ) );
  NAND2_X0P5M_A9TH \multiplier_1/U37  ( .A(\multiplier_1/n47 ), .B(
        \multiplier_1/n46 ), .Y(\multiplier_1/n19 ) );
  NAND2_X0P5M_A9TH \multiplier_1/U36  ( .A(\multiplier_1/n79 ), .B(
        \multiplier_1/n78 ), .Y(\multiplier_1/n233 ) );
  AND2_X0P5M_A9TH \multiplier_1/U35  ( .A(\multiplier_1/n194 ), .B(
        \multiplier_1/n193 ), .Y(Result_mul[14]) );
  NAND2_X0P5M_A9TH \multiplier_1/U34  ( .A(\multiplier_1/n234 ), .B(
        \multiplier_1/n233 ), .Y(\multiplier_1/n236 ) );
  NAND2_X0P5M_A9TH \multiplier_1/U33  ( .A(\multiplier_1/n82 ), .B(
        \multiplier_1/n81 ), .Y(\multiplier_1/n229 ) );
  NAND2XB_X0P5M_A9TH \multiplier_1/U32  ( .BN(\multiplier_1/n47 ), .A(
        \multiplier_1/n18 ), .Y(\multiplier_1/n20 ) );
  NAND2_X0P5M_A9TH \multiplier_1/U31  ( .A(\multiplier_1/n230 ), .B(
        \multiplier_1/n229 ), .Y(\multiplier_1/n232 ) );
  AO21B_X0P5M_A9TH \multiplier_1/U30  ( .A0(\multiplier_1/n49 ), .A1(
        \multiplier_1/n20 ), .B0N(\multiplier_1/n19 ), .Y(\multiplier_1/n92 )
         );
  NOR2_X0P5M_A9TH \multiplier_1/U29  ( .A(\multiplier_1/n85 ), .B(
        \multiplier_1/n84 ), .Y(\multiplier_1/n224 ) );
  NOR2_X0P5M_A9TH \multiplier_1/U28  ( .A(\multiplier_1/n87 ), .B(
        \multiplier_1/n86 ), .Y(\multiplier_1/n219 ) );
  NAND2_X0P5M_A9TH \multiplier_1/U27  ( .A(\multiplier_1/n85 ), .B(
        \multiplier_1/n84 ), .Y(\multiplier_1/n225 ) );
  AO21_X0P5M_A9TH \multiplier_1/U26  ( .A0(\multiplier_1/n234 ), .A1(
        \multiplier_1/n235 ), .B0(\multiplier_1/n80 ), .Y(\multiplier_1/n231 )
         );
  NAND2_X0P5M_A9TH \multiplier_1/U25  ( .A(\multiplier_1/n171 ), .B(
        \multiplier_1/n170 ), .Y(\multiplier_1/n182 ) );
  NAND2_X0P5M_A9TH \multiplier_1/U24  ( .A(\multiplier_1/n1 ), .B(
        \multiplier_1/n182 ), .Y(\multiplier_1/n183 ) );
  NAND2_X0P5M_A9TH \multiplier_1/U23  ( .A(\multiplier_1/n89 ), .B(
        \multiplier_1/n88 ), .Y(\multiplier_1/n215 ) );
  NOR2_X0P7A_A9TH \multiplier_1/U22  ( .A(\multiplier_1/n102 ), .B(
        \multiplier_1/n101 ), .Y(\multiplier_1/n200 ) );
  NAND2_X0P5M_A9TH \multiplier_1/U21  ( .A(\multiplier_1/n102 ), .B(
        \multiplier_1/n101 ), .Y(\multiplier_1/n201 ) );
  NAND2_X0P5M_A9TH \multiplier_1/U20  ( .A(\multiplier_1/n98 ), .B(
        \multiplier_1/n97 ), .Y(\multiplier_1/n211 ) );
  NAND2_X0P5M_A9TH \multiplier_1/U19  ( .A(\multiplier_1/n145 ), .B(
        \multiplier_1/n144 ), .Y(\multiplier_1/n187 ) );
  NAND2_X0P5M_A9TH \multiplier_1/U18  ( .A(\multiplier_1/n216 ), .B(
        \multiplier_1/n215 ), .Y(\multiplier_1/n218 ) );
  OA21_X0P5M_A9TH \multiplier_1/U17  ( .A0(\multiplier_1/n224 ), .A1(
        \multiplier_1/n227 ), .B0(\multiplier_1/n225 ), .Y(\multiplier_1/n222 ) );
  NOR2_X0P5M_A9TH \multiplier_1/U16  ( .A(\multiplier_1/n98 ), .B(
        \multiplier_1/n97 ), .Y(\multiplier_1/n210 ) );
  NOR2_X0P5M_A9TH \multiplier_1/U15  ( .A(\multiplier_1/n100 ), .B(
        \multiplier_1/n99 ), .Y(\multiplier_1/n205 ) );
  NAND2_X0P5M_A9TH \multiplier_1/U14  ( .A(\multiplier_1/n226 ), .B(
        \multiplier_1/n225 ), .Y(\multiplier_1/n228 ) );
  NAND2_X0P5M_A9TH \multiplier_1/U13  ( .A(\multiplier_1/n221 ), .B(
        \multiplier_1/n220 ), .Y(\multiplier_1/n223 ) );
  NAND2_X0P5M_A9TH \multiplier_1/U12  ( .A(\multiplier_1/n143 ), .B(
        \multiplier_1/n142 ), .Y(\multiplier_1/n195 ) );
  NAND2_X0P5M_A9TH \multiplier_1/U11  ( .A(\multiplier_1/n162 ), .B(
        \multiplier_1/n161 ), .Y(\multiplier_1/n178 ) );
  NAND2_X0P7M_A9TH \multiplier_1/U10  ( .A(\multiplier_1/n188 ), .B(
        \multiplier_1/n187 ), .Y(\multiplier_1/n189 ) );
  NAND2_X0P5M_A9TH \multiplier_1/U9  ( .A(\multiplier_1/n196 ), .B(
        \multiplier_1/n195 ), .Y(\multiplier_1/n197 ) );
  NAND2_X0P5M_A9TH \multiplier_1/U8  ( .A(\multiplier_1/n196 ), .B(
        \multiplier_1/n188 ), .Y(\multiplier_1/n148 ) );
  NOR2_X0P5M_A9TH \multiplier_1/U7  ( .A(\multiplier_1/n205 ), .B(
        \multiplier_1/n200 ), .Y(\multiplier_1/n104 ) );
  OAI21_X0P5M_A9TH \multiplier_1/U6  ( .A0(\multiplier_1/n200 ), .A1(
        \multiplier_1/n206 ), .B0(\multiplier_1/n201 ), .Y(\multiplier_1/n103 ) );
  NAND2_X0P5M_A9TH \multiplier_1/U5  ( .A(\multiplier_1/n202 ), .B(
        \multiplier_1/n201 ), .Y(\multiplier_1/n203 ) );
  NAND2_X0P7M_A9TH \multiplier_1/U4  ( .A(\multiplier_1/n207 ), .B(
        \multiplier_1/n206 ), .Y(\multiplier_1/n208 ) );
  NAND2_X0P7M_A9TH \multiplier_1/U3  ( .A(\multiplier_1/n212 ), .B(
        \multiplier_1/n211 ), .Y(\multiplier_1/n213 ) );
  OAI21_X0P5M_A9TH \multiplier_1/U2  ( .A0(\multiplier_1/n209 ), .A1(
        \multiplier_1/n205 ), .B0(\multiplier_1/n206 ), .Y(\multiplier_1/n204 ) );
  AO21B_X0P5M_A9TH \multiplier_1/U1  ( .A0(\multiplier_1/n174 ), .A1(
        \multiplier_1/n175 ), .B0N(\multiplier_1/n173 ), .Y(Result_mul[0]) );
  AOI222_X1M_A9TH \comparator_1/U15  ( .A0(b[0]), .A1(\comparator_1/n14 ), 
        .B0(b[0]), .B1(\comparator_1/n13 ), .C0(\comparator_1/n14 ), .C1(
        \comparator_1/n13 ), .Y(A_greater_B) );
  AOI222_X1M_A9TH \comparator_1/U14  ( .A0(a[1]), .A1(\comparator_1/n12 ), 
        .B0(a[1]), .B1(\comparator_1/n11 ), .C0(\comparator_1/n12 ), .C1(
        \comparator_1/n11 ), .Y(\comparator_1/n13 ) );
  AOI222_X1M_A9TH \comparator_1/U13  ( .A0(b[2]), .A1(\comparator_1/n10 ), 
        .B0(b[2]), .B1(\comparator_1/n9 ), .C0(\comparator_1/n10 ), .C1(
        \comparator_1/n9 ), .Y(\comparator_1/n11 ) );
  INV_X0P5B_A9TH \comparator_1/U12  ( .A(a[6]), .Y(\comparator_1/n1 ) );
  INV_X0P5B_A9TH \comparator_1/U11  ( .A(b[3]), .Y(\comparator_1/n8 ) );
  INV_X0P5B_A9TH \comparator_1/U10  ( .A(a[4]), .Y(\comparator_1/n6 ) );
  INV_X0P6M_A9TH \comparator_1/U9  ( .A(a[0]), .Y(\comparator_1/n14 ) );
  INV_X0P6M_A9TH \comparator_1/U8  ( .A(b[1]), .Y(\comparator_1/n12 ) );
  AOI222_X0P7M_A9TH \comparator_1/U7  ( .A0(b[4]), .A1(\comparator_1/n6 ), 
        .B0(b[4]), .B1(\comparator_1/n5 ), .C0(\comparator_1/n6 ), .C1(
        \comparator_1/n5 ), .Y(\comparator_1/n7 ) );
  INV_X0P6M_A9TH \comparator_1/U6  ( .A(a[2]), .Y(\comparator_1/n10 ) );
  AO21B_X0P5M_A9TH \comparator_1/U5  ( .A0(b[6]), .A1(\comparator_1/n1 ), 
        .B0N(a[7]), .Y(\comparator_1/n2 ) );
  OAI22_X0P5M_A9TH \comparator_1/U4  ( .A0(b[7]), .A1(\comparator_1/n2 ), .B0(
        \comparator_1/n1 ), .B1(b[6]), .Y(\comparator_1/n4 ) );
  AO21B_X0P5M_A9TH \comparator_1/U3  ( .A0(a[5]), .A1(\comparator_1/n4 ), 
        .B0N(b[5]), .Y(\comparator_1/n3 ) );
  OAI21_X0P5M_A9TH \comparator_1/U2  ( .A0(a[5]), .A1(\comparator_1/n4 ), .B0(
        \comparator_1/n3 ), .Y(\comparator_1/n5 ) );
  AOI222_X1M_A9TH \comparator_1/U1  ( .A0(a[3]), .A1(\comparator_1/n8 ), .B0(
        a[3]), .B1(\comparator_1/n7 ), .C0(\comparator_1/n8 ), .C1(
        \comparator_1/n7 ), .Y(\comparator_1/n9 ) );
endmodule

