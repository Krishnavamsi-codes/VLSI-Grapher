/////////////////////////////////////////////////////////////
// Created by: Synopsys DC Ultra(TM) in wire load mode
// Version   : O-2018.06-SP5-5
// Date      : Sat Sep 26 09:24:19 2020
/////////////////////////////////////////////////////////////


module add_mul_combine_8_bit ( a, b, Result_mul, Result_add );
  input [0:7] a;
  input [0:7] b;
  output [0:15] Result_mul;
  output [0:7] Result_add;
  wire   \adder_1/n1 , \adder_1/intadd_0/n1 , \adder_1/intadd_0/n2 ,
         \adder_1/intadd_0/n3 , \adder_1/intadd_0/n4 , \adder_1/intadd_0/n5 ,
         \adder_1/intadd_0/n6 , \adder_1/intadd_0/CI , \multiplier_1/n233 ,
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
         \multiplier_1/n1 ;

  NOR2_X0P5M_A9TH \adder_1/U4  ( .A(\adder_1/n1 ), .B(\adder_1/intadd_0/CI ), 
        .Y(Result_add[7]) );
  XOR3_X0P5M_A9TH \adder_1/U3  ( .A(\adder_1/intadd_0/n1 ), .B(b[0]), .C(a[0]), 
        .Y(Result_add[0]) );
  AND2_X0P5M_A9TH \adder_1/U2  ( .A(a[7]), .B(b[7]), .Y(\adder_1/intadd_0/CI )
         );
  NOR2_X0P5M_A9TH \adder_1/U1  ( .A(a[7]), .B(b[7]), .Y(\adder_1/n1 ) );
  ADDF_X1M_A9TH \adder_1/intadd_0/U2  ( .A(b[1]), .B(a[1]), .CI(
        \adder_1/intadd_0/n2 ), .CO(\adder_1/intadd_0/n1 ), .S(Result_add[1])
         );
  ADDF_X1M_A9TH \adder_1/intadd_0/U3  ( .A(b[2]), .B(a[2]), .CI(
        \adder_1/intadd_0/n3 ), .CO(\adder_1/intadd_0/n2 ), .S(Result_add[2])
         );
  ADDF_X1M_A9TH \adder_1/intadd_0/U4  ( .A(b[3]), .B(a[3]), .CI(
        \adder_1/intadd_0/n4 ), .CO(\adder_1/intadd_0/n3 ), .S(Result_add[3])
         );
  ADDF_X1M_A9TH \adder_1/intadd_0/U5  ( .A(b[4]), .B(a[4]), .CI(
        \adder_1/intadd_0/n5 ), .CO(\adder_1/intadd_0/n4 ), .S(Result_add[4])
         );
  ADDF_X1M_A9TH \adder_1/intadd_0/U6  ( .A(b[5]), .B(a[5]), .CI(
        \adder_1/intadd_0/n6 ), .CO(\adder_1/intadd_0/n5 ), .S(Result_add[5])
         );
  ADDF_X1M_A9TH \adder_1/intadd_0/U7  ( .A(b[6]), .B(a[6]), .CI(
        \adder_1/intadd_0/CI ), .CO(\adder_1/intadd_0/n6 ), .S(Result_add[6])
         );
  AND2_X0P5M_A9TH \multiplier_1/U207  ( .A(\multiplier_1/n233 ), .B(
        \multiplier_1/n232 ), .Y(Result_mul[14]) );
  OR2_X0P5M_A9TH \multiplier_1/U206  ( .A(\multiplier_1/n231 ), .B(
        \multiplier_1/n230 ), .Y(\multiplier_1/n233 ) );
  ADDF_X1M_A9TH \multiplier_1/U205  ( .A(\multiplier_1/n229 ), .B(
        \multiplier_1/n228 ), .CI(\multiplier_1/n227 ), .CO(Result_mul[0]), 
        .S(Result_mul[1]) );
  ADDF_X1M_A9TH \multiplier_1/U204  ( .A(\multiplier_1/n222 ), .B(
        \multiplier_1/n221 ), .CI(\multiplier_1/n220 ), .CO(
        \multiplier_1/n228 ), .S(\multiplier_1/n215 ) );
  XNOR2_X0P5M_A9TH \multiplier_1/U203  ( .A(\multiplier_1/n226 ), .B(
        \multiplier_1/n217 ), .Y(Result_mul[2]) );
  OR2_X0P5M_A9TH \multiplier_1/U202  ( .A(\multiplier_1/n216 ), .B(
        \multiplier_1/n215 ), .Y(\multiplier_1/n225 ) );
  ADDF_X1M_A9TH \multiplier_1/U201  ( .A(\multiplier_1/n214 ), .B(
        \multiplier_1/n213 ), .CI(\multiplier_1/n212 ), .CO(
        \multiplier_1/n220 ), .S(\multiplier_1/n208 ) );
  ADDF_X1M_A9TH \multiplier_1/U200  ( .A(\multiplier_1/n209 ), .B(
        \multiplier_1/n208 ), .CI(\multiplier_1/n207 ), .CO(
        \multiplier_1/n216 ), .S(\multiplier_1/n200 ) );
  XOR2_X0P5M_A9TH \multiplier_1/U199  ( .A(\multiplier_1/n206 ), .B(
        \multiplier_1/n203 ), .Y(Result_mul[3]) );
  NAND2_X1M_A9TH \multiplier_1/U198  ( .A(\multiplier_1/n201 ), .B(
        \multiplier_1/n200 ), .Y(\multiplier_1/n204 ) );
  ADDF_X1M_A9TH \multiplier_1/U197  ( .A(\multiplier_1/n199 ), .B(
        \multiplier_1/n198 ), .CI(\multiplier_1/n197 ), .CO(
        \multiplier_1/n207 ), .S(\multiplier_1/n190 ) );
  ADDF_X1M_A9TH \multiplier_1/U196  ( .A(\multiplier_1/n194 ), .B(
        \multiplier_1/n193 ), .CI(\multiplier_1/n192 ), .CO(
        \multiplier_1/n209 ), .S(\multiplier_1/n197 ) );
  ADDF_X1M_A9TH \multiplier_1/U195  ( .A(\multiplier_1/n191 ), .B(
        \multiplier_1/n190 ), .CI(\multiplier_1/n189 ), .CO(
        \multiplier_1/n201 ), .S(\multiplier_1/n183 ) );
  AOI21_X2M_A9TH \multiplier_1/U194  ( .A0(\multiplier_1/n188 ), .A1(
        \multiplier_1/n187 ), .B0(\multiplier_1/n186 ), .Y(\multiplier_1/n206 ) );
  XNOR2_X0P5M_A9TH \multiplier_1/U193  ( .A(\multiplier_1/n188 ), .B(
        \multiplier_1/n184 ), .Y(Result_mul[4]) );
  OR2_X0P5M_A9TH \multiplier_1/U192  ( .A(\multiplier_1/n183 ), .B(
        \multiplier_1/n182 ), .Y(\multiplier_1/n187 ) );
  ADDF_X1M_A9TH \multiplier_1/U191  ( .A(\multiplier_1/n181 ), .B(
        \multiplier_1/n180 ), .CI(\multiplier_1/n179 ), .CO(
        \multiplier_1/n182 ), .S(\multiplier_1/n154 ) );
  ADDF_X1M_A9TH \multiplier_1/U190  ( .A(\multiplier_1/n178 ), .B(
        \multiplier_1/n177 ), .CI(\multiplier_1/n176 ), .CO(
        \multiplier_1/n189 ), .S(\multiplier_1/n179 ) );
  ADDF_X1M_A9TH \multiplier_1/U189  ( .A(\multiplier_1/n173 ), .B(
        \multiplier_1/n172 ), .CI(\multiplier_1/n171 ), .CO(
        \multiplier_1/n198 ), .S(\multiplier_1/n177 ) );
  ADDF_X1M_A9TH \multiplier_1/U188  ( .A(\multiplier_1/n170 ), .B(
        \multiplier_1/n169 ), .CI(\multiplier_1/n168 ), .CO(
        \multiplier_1/n191 ), .S(\multiplier_1/n181 ) );
  OAI21_X1M_A9TH \multiplier_1/U187  ( .A0(\multiplier_1/n167 ), .A1(
        \multiplier_1/n166 ), .B0(\multiplier_1/n165 ), .Y(\multiplier_1/n188 ) );
  XNOR2_X0P5M_A9TH \multiplier_1/U186  ( .A(\multiplier_1/n164 ), .B(
        \multiplier_1/n163 ), .Y(Result_mul[6]) );
  XOR2_X0P5M_A9TH \multiplier_1/U185  ( .A(\multiplier_1/n167 ), .B(
        \multiplier_1/n156 ), .Y(Result_mul[5]) );
  ADDF_X1M_A9TH \multiplier_1/U184  ( .A(\multiplier_1/n152 ), .B(
        \multiplier_1/n151 ), .CI(\multiplier_1/n150 ), .CO(
        \multiplier_1/n153 ), .S(\multiplier_1/n132 ) );
  ADDF_X1M_A9TH \multiplier_1/U183  ( .A(\multiplier_1/n149 ), .B(
        \multiplier_1/n148 ), .CI(\multiplier_1/n147 ), .CO(
        \multiplier_1/n176 ), .S(\multiplier_1/n152 ) );
  ADDF_X1M_A9TH \multiplier_1/U182  ( .A(\multiplier_1/n144 ), .B(
        \multiplier_1/n143 ), .CI(\multiplier_1/n142 ), .CO(
        \multiplier_1/n178 ), .S(\multiplier_1/n141 ) );
  ADDF_X1M_A9TH \multiplier_1/U181  ( .A(\multiplier_1/n141 ), .B(
        \multiplier_1/n140 ), .CI(\multiplier_1/n139 ), .CO(
        \multiplier_1/n180 ), .S(\multiplier_1/n150 ) );
  ADDF_X1M_A9TH \multiplier_1/U180  ( .A(\multiplier_1/n138 ), .B(
        \multiplier_1/n137 ), .CI(\multiplier_1/n136 ), .CO(
        \multiplier_1/n168 ), .S(\multiplier_1/n140 ) );
  AOI21_X1M_A9TH \multiplier_1/U179  ( .A0(\multiplier_1/n135 ), .A1(
        \multiplier_1/n134 ), .B0(\multiplier_1/n133 ), .Y(\multiplier_1/n167 ) );
  NOR2_X1A_A9TH \multiplier_1/U178  ( .A(\multiplier_1/n132 ), .B(
        \multiplier_1/n131 ), .Y(\multiplier_1/n160 ) );
  ADDF_X1M_A9TH \multiplier_1/U177  ( .A(\multiplier_1/n130 ), .B(
        \multiplier_1/n129 ), .CI(\multiplier_1/n128 ), .CO(
        \multiplier_1/n131 ), .S(\multiplier_1/n109 ) );
  ADDF_X1M_A9TH \multiplier_1/U176  ( .A(\multiplier_1/n127 ), .B(
        \multiplier_1/n126 ), .CI(\multiplier_1/n125 ), .CO(
        \multiplier_1/n139 ), .S(\multiplier_1/n130 ) );
  NOR2_X1A_A9TH \multiplier_1/U175  ( .A(\multiplier_1/n124 ), .B(
        \multiplier_1/n218 ), .Y(\multiplier_1/n137 ) );
  NOR2_X1A_A9TH \multiplier_1/U174  ( .A(\multiplier_1/n219 ), .B(
        \multiplier_1/n123 ), .Y(\multiplier_1/n138 ) );
  NOR2_X1A_A9TH \multiplier_1/U173  ( .A(\multiplier_1/n175 ), .B(
        \multiplier_1/n195 ), .Y(\multiplier_1/n143 ) );
  NOR2_X1A_A9TH \multiplier_1/U172  ( .A(\multiplier_1/n211 ), .B(
        \multiplier_1/n145 ), .Y(\multiplier_1/n144 ) );
  ADDF_X1M_A9TH \multiplier_1/U171  ( .A(\multiplier_1/n122 ), .B(
        \multiplier_1/n121 ), .CI(\multiplier_1/n120 ), .CO(
        \multiplier_1/n151 ), .S(\multiplier_1/n128 ) );
  ADDF_X1M_A9TH \multiplier_1/U170  ( .A(\multiplier_1/n119 ), .B(
        \multiplier_1/n118 ), .CI(\multiplier_1/n117 ), .CO(
        \multiplier_1/n147 ), .S(\multiplier_1/n120 ) );
  ADDF_X1M_A9TH \multiplier_1/U169  ( .A(\multiplier_1/n116 ), .B(
        \multiplier_1/n115 ), .CI(\multiplier_1/n114 ), .CO(
        \multiplier_1/n148 ), .S(\multiplier_1/n122 ) );
  ADDH_X1M_A9TH \multiplier_1/U168  ( .A(\multiplier_1/n113 ), .B(
        \multiplier_1/n112 ), .CO(\multiplier_1/n149 ), .S(\multiplier_1/n127 ) );
  XOR2_X0P5M_A9TH \multiplier_1/U167  ( .A(\multiplier_1/n159 ), .B(
        \multiplier_1/n111 ), .Y(Result_mul[7]) );
  NAND2_X1M_A9TH \multiplier_1/U166  ( .A(\multiplier_1/n109 ), .B(
        \multiplier_1/n108 ), .Y(\multiplier_1/n157 ) );
  NOR2_X1A_A9TH \multiplier_1/U165  ( .A(\multiplier_1/n109 ), .B(
        \multiplier_1/n108 ), .Y(\multiplier_1/n158 ) );
  ADDF_X1M_A9TH \multiplier_1/U164  ( .A(\multiplier_1/n107 ), .B(
        \multiplier_1/n106 ), .CI(\multiplier_1/n105 ), .CO(
        \multiplier_1/n108 ), .S(\multiplier_1/n83 ) );
  ADDH_X1M_A9TH \multiplier_1/U163  ( .A(\multiplier_1/n104 ), .B(
        \multiplier_1/n103 ), .CO(\multiplier_1/n117 ), .S(\multiplier_1/n101 ) );
  ADDF_X1M_A9TH \multiplier_1/U162  ( .A(\multiplier_1/n102 ), .B(
        \multiplier_1/n101 ), .CI(\multiplier_1/n100 ), .CO(
        \multiplier_1/n121 ), .S(\multiplier_1/n107 ) );
  NOR2_X1A_A9TH \multiplier_1/U161  ( .A(\multiplier_1/n146 ), .B(
        \multiplier_1/n195 ), .Y(\multiplier_1/n115 ) );
  NOR2_X1A_A9TH \multiplier_1/U160  ( .A(\multiplier_1/n175 ), .B(
        \multiplier_1/n174 ), .Y(\multiplier_1/n116 ) );
  ADDF_X1M_A9TH \multiplier_1/U159  ( .A(\multiplier_1/n98 ), .B(
        \multiplier_1/n97 ), .CI(\multiplier_1/n96 ), .CO(\multiplier_1/n129 ), 
        .S(\multiplier_1/n105 ) );
  ADDF_X1M_A9TH \multiplier_1/U158  ( .A(\multiplier_1/n95 ), .B(
        \multiplier_1/n94 ), .CI(\multiplier_1/n93 ), .CO(\multiplier_1/n125 ), 
        .S(\multiplier_1/n97 ) );
  ADDF_X1M_A9TH \multiplier_1/U157  ( .A(\multiplier_1/n92 ), .B(
        \multiplier_1/n91 ), .CI(\multiplier_1/n90 ), .CO(\multiplier_1/n126 ), 
        .S(\multiplier_1/n96 ) );
  XOR2_X0P5M_A9TH \multiplier_1/U156  ( .A(\multiplier_1/n88 ), .B(
        \multiplier_1/n85 ), .Y(Result_mul[8]) );
  ADDF_X1M_A9TH \multiplier_1/U155  ( .A(\multiplier_1/n81 ), .B(
        \multiplier_1/n80 ), .CI(\multiplier_1/n79 ), .CO(\multiplier_1/n82 ), 
        .S(\multiplier_1/n54 ) );
  NOR2_X1A_A9TH \multiplier_1/U154  ( .A(\multiplier_1/n124 ), .B(
        \multiplier_1/n195 ), .Y(\multiplier_1/n91 ) );
  NOR2_X1A_A9TH \multiplier_1/U153  ( .A(\multiplier_1/n219 ), .B(
        \multiplier_1/n78 ), .Y(\multiplier_1/n92 ) );
  NOR2_X1A_A9TH \multiplier_1/U152  ( .A(\multiplier_1/n175 ), .B(
        \multiplier_1/n145 ), .Y(\multiplier_1/n94 ) );
  NOR2_X1A_A9TH \multiplier_1/U151  ( .A(\multiplier_1/n146 ), .B(
        \multiplier_1/n174 ), .Y(\multiplier_1/n95 ) );
  ADDF_X1M_A9TH \multiplier_1/U150  ( .A(\multiplier_1/n77 ), .B(
        \multiplier_1/n76 ), .CI(\multiplier_1/n75 ), .CO(\multiplier_1/n98 ), 
        .S(\multiplier_1/n80 ) );
  ADDF_X1M_A9TH \multiplier_1/U149  ( .A(\multiplier_1/n68 ), .B(
        \multiplier_1/n67 ), .CI(\multiplier_1/n66 ), .CO(\multiplier_1/n100 ), 
        .S(\multiplier_1/n74 ) );
  ADDH_X1M_A9TH \multiplier_1/U148  ( .A(\multiplier_1/n64 ), .B(
        \multiplier_1/n63 ), .CO(\multiplier_1/n102 ), .S(\multiplier_1/n70 )
         );
  XNOR2_X0P5M_A9TH \multiplier_1/U147  ( .A(\multiplier_1/n58 ), .B(
        \multiplier_1/n61 ), .Y(Result_mul[9]) );
  OAI21_X1M_A9TH \multiplier_1/U146  ( .A0(\multiplier_1/n57 ), .A1(
        \multiplier_1/n56 ), .B0(\multiplier_1/n55 ), .Y(\multiplier_1/n61 )
         );
  OR2_X0P5M_A9TH \multiplier_1/U145  ( .A(\multiplier_1/n54 ), .B(
        \multiplier_1/n53 ), .Y(\multiplier_1/n62 ) );
  ADDF_X1M_A9TH \multiplier_1/U144  ( .A(\multiplier_1/n52 ), .B(
        \multiplier_1/n51 ), .CI(\multiplier_1/n50 ), .CO(\multiplier_1/n53 ), 
        .S(\multiplier_1/n35 ) );
  ADDF_X1M_A9TH \multiplier_1/U143  ( .A(\multiplier_1/n48 ), .B(
        \multiplier_1/n47 ), .CI(\multiplier_1/n46 ), .CO(\multiplier_1/n71 ), 
        .S(\multiplier_1/n51 ) );
  NOR2_X1A_A9TH \multiplier_1/U142  ( .A(\multiplier_1/n124 ), .B(
        \multiplier_1/n174 ), .Y(\multiplier_1/n67 ) );
  NOR2_X1A_A9TH \multiplier_1/U141  ( .A(\multiplier_1/n211 ), .B(
        \multiplier_1/n78 ), .Y(\multiplier_1/n68 ) );
  ADDH_X1M_A9TH \multiplier_1/U140  ( .A(\multiplier_1/n45 ), .B(
        \multiplier_1/n44 ), .CO(\multiplier_1/n75 ), .S(\multiplier_1/n41 )
         );
  ADDF_X1M_A9TH \multiplier_1/U139  ( .A(\multiplier_1/n43 ), .B(
        \multiplier_1/n42 ), .CI(\multiplier_1/n41 ), .CO(\multiplier_1/n81 ), 
        .S(\multiplier_1/n50 ) );
  XOR2_X0P5M_A9TH \multiplier_1/U138  ( .A(\multiplier_1/n40 ), .B(
        \multiplier_1/n56 ), .Y(Result_mul[10]) );
  ADDF_X1M_A9TH \multiplier_1/U137  ( .A(\multiplier_1/n33 ), .B(
        \multiplier_1/n32 ), .CI(\multiplier_1/n31 ), .CO(\multiplier_1/n34 ), 
        .S(\multiplier_1/n19 ) );
  ADDH_X1M_A9TH \multiplier_1/U136  ( .A(\multiplier_1/n30 ), .B(
        \multiplier_1/n29 ), .CO(\multiplier_1/n42 ), .S(\multiplier_1/n32 )
         );
  NOR2_X1A_A9TH \multiplier_1/U135  ( .A(\multiplier_1/n124 ), .B(
        \multiplier_1/n145 ), .Y(\multiplier_1/n47 ) );
  NOR2_X1A_A9TH \multiplier_1/U134  ( .A(\multiplier_1/n196 ), .B(
        \multiplier_1/n78 ), .Y(\multiplier_1/n48 ) );
  ADDF_X1M_A9TH \multiplier_1/U133  ( .A(\multiplier_1/n28 ), .B(
        \multiplier_1/n27 ), .CI(\multiplier_1/n26 ), .CO(\multiplier_1/n52 ), 
        .S(\multiplier_1/n18 ) );
  XOR2_X0P5M_A9TH \multiplier_1/U132  ( .A(\multiplier_1/n25 ), .B(
        \multiplier_1/n38 ), .Y(Result_mul[11]) );
  ADDF_X1M_A9TH \multiplier_1/U131  ( .A(\multiplier_1/n17 ), .B(
        \multiplier_1/n16 ), .CI(\multiplier_1/n15 ), .CO(\multiplier_1/n31 ), 
        .S(\multiplier_1/n7 ) );
  ADDH_X1M_A9TH \multiplier_1/U130  ( .A(\multiplier_1/n14 ), .B(
        \multiplier_1/n13 ), .CO(\multiplier_1/n33 ), .S(\multiplier_1/n6 ) );
  XNOR2_X0P5M_A9TH \multiplier_1/U129  ( .A(\multiplier_1/n12 ), .B(
        \multiplier_1/n23 ), .Y(Result_mul[12]) );
  OR2_X0P5M_A9TH \multiplier_1/U128  ( .A(\multiplier_1/n7 ), .B(
        \multiplier_1/n6 ), .Y(\multiplier_1/n24 ) );
  ADDH_X1M_A9TH \multiplier_1/U127  ( .A(\multiplier_1/n5 ), .B(
        \multiplier_1/n4 ), .CO(\multiplier_1/n15 ), .S(\multiplier_1/n2 ) );
  XNOR2_X0P5M_A9TH \multiplier_1/U126  ( .A(\multiplier_1/n3 ), .B(
        \multiplier_1/n10 ), .Y(Result_mul[13]) );
  OR2_X0P5M_A9TH \multiplier_1/U125  ( .A(\multiplier_1/n2 ), .B(
        \multiplier_1/n1 ), .Y(\multiplier_1/n11 ) );
  NOR2_X0P5M_A9TH \multiplier_1/U124  ( .A(\multiplier_1/n65 ), .B(
        \multiplier_1/n78 ), .Y(Result_mul[15]) );
  INV_X0P5B_A9TH \multiplier_1/U123  ( .A(\multiplier_1/n205 ), .Y(
        \multiplier_1/n202 ) );
  INV_X0P5B_A9TH \multiplier_1/U122  ( .A(\multiplier_1/n166 ), .Y(
        \multiplier_1/n155 ) );
  INV_X0P5B_A9TH \multiplier_1/U121  ( .A(\multiplier_1/n160 ), .Y(
        \multiplier_1/n162 ) );
  INV_X0P5B_A9TH \multiplier_1/U120  ( .A(\multiplier_1/n158 ), .Y(
        \multiplier_1/n110 ) );
  INV_X0P5B_A9TH \multiplier_1/U119  ( .A(\multiplier_1/n87 ), .Y(
        \multiplier_1/n84 ) );
  INV_X0P5B_A9TH \multiplier_1/U118  ( .A(\multiplier_1/n57 ), .Y(
        \multiplier_1/n36 ) );
  INV_X0P5B_A9TH \multiplier_1/U117  ( .A(\multiplier_1/n39 ), .Y(
        \multiplier_1/n20 ) );
  INV_X0P5B_A9TH \multiplier_1/U116  ( .A(\multiplier_1/n232 ), .Y(
        \multiplier_1/n10 ) );
  INV_X0P5B_A9TH \multiplier_1/U115  ( .A(\multiplier_1/n70 ), .Y(
        \multiplier_1/n69 ) );
  INV_X0P5B_A9TH \multiplier_1/U114  ( .A(\multiplier_1/n21 ), .Y(
        \multiplier_1/n22 ) );
  AOI21_X0P7M_A9TH \multiplier_1/U113  ( .A0(\multiplier_1/n24 ), .A1(
        \multiplier_1/n23 ), .B0(\multiplier_1/n22 ), .Y(\multiplier_1/n38 )
         );
  INV_X0P5B_A9TH \multiplier_1/U112  ( .A(\multiplier_1/n8 ), .Y(
        \multiplier_1/n9 ) );
  OAI21_X1M_A9TH \multiplier_1/U111  ( .A0(\multiplier_1/n88 ), .A1(
        \multiplier_1/n87 ), .B0(\multiplier_1/n86 ), .Y(\multiplier_1/n134 )
         );
  INV_X1M_A9TH \multiplier_1/U110  ( .A(a[1]), .Y(\multiplier_1/n210 ) );
  INV_X1M_A9TH \multiplier_1/U109  ( .A(a[3]), .Y(\multiplier_1/n174 ) );
  NOR2_X0P7A_A9TH \multiplier_1/U108  ( .A(\multiplier_1/n89 ), .B(
        \multiplier_1/n195 ), .Y(\multiplier_1/n63 ) );
  NOR2_X0P7A_A9TH \multiplier_1/U107  ( .A(\multiplier_1/n65 ), .B(
        \multiplier_1/n210 ), .Y(\multiplier_1/n64 ) );
  NOR2_X0P7A_A9TH \multiplier_1/U106  ( .A(\multiplier_1/n219 ), .B(
        \multiplier_1/n218 ), .Y(\multiplier_1/n229 ) );
  NOR2_X0P7A_A9TH \multiplier_1/U105  ( .A(\multiplier_1/n146 ), .B(
        \multiplier_1/n123 ), .Y(\multiplier_1/n46 ) );
  NOR2_X0P7A_A9TH \multiplier_1/U104  ( .A(\multiplier_1/n211 ), .B(
        \multiplier_1/n218 ), .Y(\multiplier_1/n221 ) );
  NOR2_X0P7A_A9TH \multiplier_1/U103  ( .A(\multiplier_1/n196 ), .B(
        \multiplier_1/n218 ), .Y(\multiplier_1/n213 ) );
  NOR2_X0P7A_A9TH \multiplier_1/U102  ( .A(\multiplier_1/n211 ), .B(
        \multiplier_1/n195 ), .Y(\multiplier_1/n199 ) );
  NOR2_X0P7A_A9TH \multiplier_1/U101  ( .A(\multiplier_1/n175 ), .B(
        \multiplier_1/n218 ), .Y(\multiplier_1/n193 ) );
  NOR2_X0P7A_A9TH \multiplier_1/U100  ( .A(\multiplier_1/n219 ), .B(
        \multiplier_1/n195 ), .Y(\multiplier_1/n214 ) );
  NOR2_X0P7A_A9TH \multiplier_1/U99  ( .A(\multiplier_1/n219 ), .B(
        \multiplier_1/n210 ), .Y(\multiplier_1/n222 ) );
  NOR2_X0P7A_A9TH \multiplier_1/U98  ( .A(\multiplier_1/n219 ), .B(
        \multiplier_1/n174 ), .Y(\multiplier_1/n194 ) );
  XOR2_X0P5M_A9TH \multiplier_1/U97  ( .A(\multiplier_1/n71 ), .B(
        \multiplier_1/n70 ), .Y(\multiplier_1/n49 ) );
  XOR2_X0P5M_A9TH \multiplier_1/U96  ( .A(\multiplier_1/n74 ), .B(
        \multiplier_1/n49 ), .Y(\multiplier_1/n79 ) );
  NAND2_X0P7M_A9TH \multiplier_1/U95  ( .A(\multiplier_1/n19 ), .B(
        \multiplier_1/n18 ), .Y(\multiplier_1/n37 ) );
  AO21B_X0P7M_A9TH \multiplier_1/U94  ( .A0(\multiplier_1/n74 ), .A1(
        \multiplier_1/n73 ), .B0N(\multiplier_1/n72 ), .Y(\multiplier_1/n106 )
         );
  NAND2_X0P7M_A9TH \multiplier_1/U93  ( .A(\multiplier_1/n35 ), .B(
        \multiplier_1/n34 ), .Y(\multiplier_1/n55 ) );
  NAND2_X0P7M_A9TH \multiplier_1/U92  ( .A(\multiplier_1/n54 ), .B(
        \multiplier_1/n53 ), .Y(\multiplier_1/n59 ) );
  NAND2_X0P7M_A9TH \multiplier_1/U91  ( .A(\multiplier_1/n154 ), .B(
        \multiplier_1/n153 ), .Y(\multiplier_1/n165 ) );
  NAND2_X0P7M_A9TH \multiplier_1/U90  ( .A(\multiplier_1/n132 ), .B(
        \multiplier_1/n131 ), .Y(\multiplier_1/n161 ) );
  NOR2_X0P7A_A9TH \multiplier_1/U89  ( .A(\multiplier_1/n201 ), .B(
        \multiplier_1/n200 ), .Y(\multiplier_1/n205 ) );
  NAND2_X0P7M_A9TH \multiplier_1/U88  ( .A(\multiplier_1/n183 ), .B(
        \multiplier_1/n182 ), .Y(\multiplier_1/n185 ) );
  INV_X0P6M_A9TH \multiplier_1/U87  ( .A(\multiplier_1/n223 ), .Y(
        \multiplier_1/n224 ) );
  NAND2_X0P7M_A9TH \multiplier_1/U86  ( .A(\multiplier_1/n83 ), .B(
        \multiplier_1/n82 ), .Y(\multiplier_1/n86 ) );
  NAND2_X0P5M_A9TH \multiplier_1/U85  ( .A(\multiplier_1/n225 ), .B(
        \multiplier_1/n223 ), .Y(\multiplier_1/n217 ) );
  AOI21_X1M_A9TH \multiplier_1/U84  ( .A0(\multiplier_1/n62 ), .A1(
        \multiplier_1/n61 ), .B0(\multiplier_1/n60 ), .Y(\multiplier_1/n88 )
         );
  OAI21_X0P7M_A9TH \multiplier_1/U83  ( .A0(\multiplier_1/n159 ), .A1(
        \multiplier_1/n158 ), .B0(\multiplier_1/n157 ), .Y(\multiplier_1/n164 ) );
  AO21_X1M_A9TH \multiplier_1/U82  ( .A0(\multiplier_1/n226 ), .A1(
        \multiplier_1/n225 ), .B0(\multiplier_1/n224 ), .Y(\multiplier_1/n227 ) );
  INV_X0P7M_A9TH \multiplier_1/U81  ( .A(b[4]), .Y(\multiplier_1/n146 ) );
  INV_X0P7M_A9TH \multiplier_1/U80  ( .A(a[6]), .Y(\multiplier_1/n99 ) );
  INV_X0P7M_A9TH \multiplier_1/U79  ( .A(b[6]), .Y(\multiplier_1/n89 ) );
  INV_X0P7M_A9TH \multiplier_1/U78  ( .A(b[7]), .Y(\multiplier_1/n65 ) );
  INV_X0P7M_A9TH \multiplier_1/U77  ( .A(a[4]), .Y(\multiplier_1/n145 ) );
  INV_X0P7M_A9TH \multiplier_1/U76  ( .A(b[1]), .Y(\multiplier_1/n211 ) );
  INV_X0P7M_A9TH \multiplier_1/U75  ( .A(b[0]), .Y(\multiplier_1/n219 ) );
  INV_X0P7M_A9TH \multiplier_1/U74  ( .A(b[3]), .Y(\multiplier_1/n175 ) );
  INV_X0P7M_A9TH \multiplier_1/U73  ( .A(a[7]), .Y(\multiplier_1/n78 ) );
  INV_X0P7M_A9TH \multiplier_1/U72  ( .A(b[2]), .Y(\multiplier_1/n196 ) );
  INV_X0P7M_A9TH \multiplier_1/U71  ( .A(a[0]), .Y(\multiplier_1/n218 ) );
  INV_X0P7M_A9TH \multiplier_1/U70  ( .A(b[5]), .Y(\multiplier_1/n124 ) );
  INV_X0P7M_A9TH \multiplier_1/U69  ( .A(a[5]), .Y(\multiplier_1/n123 ) );
  INV_X0P7M_A9TH \multiplier_1/U68  ( .A(a[2]), .Y(\multiplier_1/n195 ) );
  NOR2_X0P5M_A9TH \multiplier_1/U67  ( .A(\multiplier_1/n175 ), .B(
        \multiplier_1/n210 ), .Y(\multiplier_1/n171 ) );
  NOR2_X0P5M_A9TH \multiplier_1/U66  ( .A(\multiplier_1/n219 ), .B(
        \multiplier_1/n145 ), .Y(\multiplier_1/n173 ) );
  NOR2_X0P5M_A9TH \multiplier_1/U65  ( .A(\multiplier_1/n146 ), .B(
        \multiplier_1/n218 ), .Y(\multiplier_1/n172 ) );
  NOR2_X0P5M_A9TH \multiplier_1/U64  ( .A(\multiplier_1/n196 ), .B(
        \multiplier_1/n210 ), .Y(\multiplier_1/n192 ) );
  NOR2_X0P5M_A9TH \multiplier_1/U63  ( .A(\multiplier_1/n89 ), .B(
        \multiplier_1/n99 ), .Y(\multiplier_1/n5 ) );
  NOR2_X0P5M_A9TH \multiplier_1/U62  ( .A(\multiplier_1/n89 ), .B(
        \multiplier_1/n174 ), .Y(\multiplier_1/n44 ) );
  NOR2_X0P5M_A9TH \multiplier_1/U61  ( .A(\multiplier_1/n124 ), .B(
        \multiplier_1/n99 ), .Y(\multiplier_1/n16 ) );
  NOR2_X0P5M_A9TH \multiplier_1/U60  ( .A(\multiplier_1/n65 ), .B(
        \multiplier_1/n195 ), .Y(\multiplier_1/n45 ) );
  NOR2_X0P5M_A9TH \multiplier_1/U59  ( .A(\multiplier_1/n89 ), .B(
        \multiplier_1/n123 ), .Y(\multiplier_1/n13 ) );
  NOR2_X0P5M_A9TH \multiplier_1/U58  ( .A(\multiplier_1/n196 ), .B(
        \multiplier_1/n99 ), .Y(\multiplier_1/n66 ) );
  NOR2_X0P5M_A9TH \multiplier_1/U57  ( .A(\multiplier_1/n146 ), .B(
        \multiplier_1/n145 ), .Y(\multiplier_1/n76 ) );
  NOR2_X0P5M_A9TH \multiplier_1/U56  ( .A(\multiplier_1/n146 ), .B(
        \multiplier_1/n78 ), .Y(\multiplier_1/n17 ) );
  NOR2_X0P5M_A9TH \multiplier_1/U55  ( .A(\multiplier_1/n65 ), .B(
        \multiplier_1/n145 ), .Y(\multiplier_1/n14 ) );
  NOR2_X0P5M_A9TH \multiplier_1/U54  ( .A(\multiplier_1/n65 ), .B(
        \multiplier_1/n123 ), .Y(\multiplier_1/n1 ) );
  NOR2_X0P5M_A9TH \multiplier_1/U53  ( .A(\multiplier_1/n211 ), .B(
        \multiplier_1/n99 ), .Y(\multiplier_1/n90 ) );
  NOR2_X0P5M_A9TH \multiplier_1/U52  ( .A(\multiplier_1/n175 ), .B(
        \multiplier_1/n123 ), .Y(\multiplier_1/n77 ) );
  NOR2_X0P5M_A9TH \multiplier_1/U51  ( .A(\multiplier_1/n124 ), .B(
        \multiplier_1/n78 ), .Y(\multiplier_1/n4 ) );
  NOR2_X0P5M_A9TH \multiplier_1/U50  ( .A(\multiplier_1/n65 ), .B(
        \multiplier_1/n99 ), .Y(\multiplier_1/n230 ) );
  NOR2_X0P5M_A9TH \multiplier_1/U49  ( .A(\multiplier_1/n89 ), .B(
        \multiplier_1/n78 ), .Y(\multiplier_1/n231 ) );
  NOR2_X0P5M_A9TH \multiplier_1/U48  ( .A(\multiplier_1/n124 ), .B(
        \multiplier_1/n123 ), .Y(\multiplier_1/n27 ) );
  NOR2_X0P5M_A9TH \multiplier_1/U47  ( .A(\multiplier_1/n89 ), .B(
        \multiplier_1/n210 ), .Y(\multiplier_1/n103 ) );
  NOR2_X0P5M_A9TH \multiplier_1/U46  ( .A(\multiplier_1/n175 ), .B(
        \multiplier_1/n78 ), .Y(\multiplier_1/n28 ) );
  NOR2_X0P5M_A9TH \multiplier_1/U45  ( .A(\multiplier_1/n196 ), .B(
        \multiplier_1/n123 ), .Y(\multiplier_1/n93 ) );
  NOR2_X0P5M_A9TH \multiplier_1/U44  ( .A(\multiplier_1/n65 ), .B(
        \multiplier_1/n218 ), .Y(\multiplier_1/n104 ) );
  NOR2_X0P5M_A9TH \multiplier_1/U43  ( .A(\multiplier_1/n146 ), .B(
        \multiplier_1/n210 ), .Y(\multiplier_1/n136 ) );
  NOR2_X0P5M_A9TH \multiplier_1/U42  ( .A(\multiplier_1/n196 ), .B(
        \multiplier_1/n174 ), .Y(\multiplier_1/n142 ) );
  NOR2_X0P5M_A9TH \multiplier_1/U41  ( .A(\multiplier_1/n219 ), .B(
        \multiplier_1/n99 ), .Y(\multiplier_1/n114 ) );
  NOR2_X0P5M_A9TH \multiplier_1/U40  ( .A(\multiplier_1/n196 ), .B(
        \multiplier_1/n145 ), .Y(\multiplier_1/n118 ) );
  NOR2_X0P5M_A9TH \multiplier_1/U39  ( .A(\multiplier_1/n146 ), .B(
        \multiplier_1/n99 ), .Y(\multiplier_1/n26 ) );
  NOR2_X0P5M_A9TH \multiplier_1/U38  ( .A(\multiplier_1/n89 ), .B(
        \multiplier_1/n218 ), .Y(\multiplier_1/n113 ) );
  NOR2_X0P5M_A9TH \multiplier_1/U37  ( .A(\multiplier_1/n211 ), .B(
        \multiplier_1/n174 ), .Y(\multiplier_1/n170 ) );
  NOR2_X0P5M_A9TH \multiplier_1/U36  ( .A(\multiplier_1/n211 ), .B(
        \multiplier_1/n123 ), .Y(\multiplier_1/n119 ) );
  NOR2_X0P5M_A9TH \multiplier_1/U35  ( .A(\multiplier_1/n211 ), .B(
        \multiplier_1/n210 ), .Y(\multiplier_1/n212 ) );
  NOR2_X0P5M_A9TH \multiplier_1/U34  ( .A(\multiplier_1/n196 ), .B(
        \multiplier_1/n195 ), .Y(\multiplier_1/n169 ) );
  NOR2_X0P5M_A9TH \multiplier_1/U33  ( .A(\multiplier_1/n65 ), .B(
        \multiplier_1/n174 ), .Y(\multiplier_1/n30 ) );
  NOR2_X0P5M_A9TH \multiplier_1/U32  ( .A(\multiplier_1/n89 ), .B(
        \multiplier_1/n145 ), .Y(\multiplier_1/n29 ) );
  NOR2_X0P5M_A9TH \multiplier_1/U31  ( .A(\multiplier_1/n124 ), .B(
        \multiplier_1/n210 ), .Y(\multiplier_1/n112 ) );
  NOR2_X0P5M_A9TH \multiplier_1/U30  ( .A(\multiplier_1/n175 ), .B(
        \multiplier_1/n99 ), .Y(\multiplier_1/n43 ) );
  NAND2_X0P5M_A9TH \multiplier_1/U29  ( .A(\multiplier_1/n231 ), .B(
        \multiplier_1/n230 ), .Y(\multiplier_1/n232 ) );
  NAND2_X0P5M_A9TH \multiplier_1/U28  ( .A(\multiplier_1/n2 ), .B(
        \multiplier_1/n1 ), .Y(\multiplier_1/n8 ) );
  NAND2_X0P5M_A9TH \multiplier_1/U27  ( .A(\multiplier_1/n71 ), .B(
        \multiplier_1/n70 ), .Y(\multiplier_1/n72 ) );
  NAND2_X0P5M_A9TH \multiplier_1/U26  ( .A(\multiplier_1/n7 ), .B(
        \multiplier_1/n6 ), .Y(\multiplier_1/n21 ) );
  NAND2_X0P5M_A9TH \multiplier_1/U25  ( .A(\multiplier_1/n11 ), .B(
        \multiplier_1/n8 ), .Y(\multiplier_1/n3 ) );
  NAND2XB_X0P5M_A9TH \multiplier_1/U24  ( .BN(\multiplier_1/n71 ), .A(
        \multiplier_1/n69 ), .Y(\multiplier_1/n73 ) );
  NAND2_X1M_A9TH \multiplier_1/U23  ( .A(\multiplier_1/n216 ), .B(
        \multiplier_1/n215 ), .Y(\multiplier_1/n223 ) );
  NOR2_X0P5M_A9TH \multiplier_1/U22  ( .A(\multiplier_1/n19 ), .B(
        \multiplier_1/n18 ), .Y(\multiplier_1/n39 ) );
  NAND2_X0P5M_A9TH \multiplier_1/U21  ( .A(\multiplier_1/n24 ), .B(
        \multiplier_1/n21 ), .Y(\multiplier_1/n12 ) );
  AO21_X0P5M_A9TH \multiplier_1/U20  ( .A0(\multiplier_1/n11 ), .A1(
        \multiplier_1/n10 ), .B0(\multiplier_1/n9 ), .Y(\multiplier_1/n23 ) );
  NOR2_X0P5M_A9TH \multiplier_1/U19  ( .A(\multiplier_1/n35 ), .B(
        \multiplier_1/n34 ), .Y(\multiplier_1/n57 ) );
  NOR2_X0P5M_A9TH \multiplier_1/U18  ( .A(\multiplier_1/n83 ), .B(
        \multiplier_1/n82 ), .Y(\multiplier_1/n87 ) );
  NAND2_X0P5M_A9TH \multiplier_1/U17  ( .A(\multiplier_1/n20 ), .B(
        \multiplier_1/n37 ), .Y(\multiplier_1/n25 ) );
  NAND2_X0P5M_A9TH \multiplier_1/U16  ( .A(\multiplier_1/n62 ), .B(
        \multiplier_1/n59 ), .Y(\multiplier_1/n58 ) );
  NAND2_X0P5M_A9TH \multiplier_1/U15  ( .A(\multiplier_1/n36 ), .B(
        \multiplier_1/n55 ), .Y(\multiplier_1/n40 ) );
  NOR2_X0P5M_A9TH \multiplier_1/U14  ( .A(\multiplier_1/n154 ), .B(
        \multiplier_1/n153 ), .Y(\multiplier_1/n166 ) );
  INV_X0P7M_A9TH \multiplier_1/U13  ( .A(\multiplier_1/n59 ), .Y(
        \multiplier_1/n60 ) );
  OA21_X0P5M_A9TH \multiplier_1/U12  ( .A0(\multiplier_1/n39 ), .A1(
        \multiplier_1/n38 ), .B0(\multiplier_1/n37 ), .Y(\multiplier_1/n56 )
         );
  NAND2_X0P5M_A9TH \multiplier_1/U11  ( .A(\multiplier_1/n162 ), .B(
        \multiplier_1/n161 ), .Y(\multiplier_1/n163 ) );
  INV_X0P6M_A9TH \multiplier_1/U10  ( .A(\multiplier_1/n185 ), .Y(
        \multiplier_1/n186 ) );
  NOR2_X0P5M_A9TH \multiplier_1/U9  ( .A(\multiplier_1/n158 ), .B(
        \multiplier_1/n160 ), .Y(\multiplier_1/n135 ) );
  OAI21_X0P5M_A9TH \multiplier_1/U8  ( .A0(\multiplier_1/n160 ), .A1(
        \multiplier_1/n157 ), .B0(\multiplier_1/n161 ), .Y(\multiplier_1/n133 ) );
  NAND2_X0P5M_A9TH \multiplier_1/U7  ( .A(\multiplier_1/n187 ), .B(
        \multiplier_1/n185 ), .Y(\multiplier_1/n184 ) );
  NAND2_X0P5M_A9TH \multiplier_1/U6  ( .A(\multiplier_1/n155 ), .B(
        \multiplier_1/n165 ), .Y(\multiplier_1/n156 ) );
  NAND2_X0P5M_A9TH \multiplier_1/U5  ( .A(\multiplier_1/n110 ), .B(
        \multiplier_1/n157 ), .Y(\multiplier_1/n111 ) );
  NAND2_X0P7M_A9TH \multiplier_1/U4  ( .A(\multiplier_1/n84 ), .B(
        \multiplier_1/n86 ), .Y(\multiplier_1/n85 ) );
  NAND2_X0P5M_A9TH \multiplier_1/U3  ( .A(\multiplier_1/n202 ), .B(
        \multiplier_1/n204 ), .Y(\multiplier_1/n203 ) );
  INV_X0P6M_A9TH \multiplier_1/U2  ( .A(\multiplier_1/n134 ), .Y(
        \multiplier_1/n159 ) );
  OAI21_X1M_A9TH \multiplier_1/U1  ( .A0(\multiplier_1/n206 ), .A1(
        \multiplier_1/n205 ), .B0(\multiplier_1/n204 ), .Y(\multiplier_1/n226 ) );
endmodule

