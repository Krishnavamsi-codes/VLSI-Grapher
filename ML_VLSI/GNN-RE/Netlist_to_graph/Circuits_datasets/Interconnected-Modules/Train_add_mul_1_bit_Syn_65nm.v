/////////////////////////////////////////////////////////////
// Created by: Synopsys DC Ultra(TM) in wire load mode
// Version   : O-2018.06-SP5-5
// Date      : Fri Sep 25 09:55:16 2020
/////////////////////////////////////////////////////////////


module add_mul_1_bit ( a, b, operation, Result );
  input a, b, operation;
  output Result;
  wire   Result_add, Result_mul;

  MX2_X0P5M_A9TH U2 ( .A(Result_add), .B(Result_mul), .S0(operation), .Y(
        Result) );
  XOR2_X0P5M_A9TH \adder_1/U1  ( .A(b), .B(a), .Y(Result_add) );
  AND2_X1M_A9TH \multiplier_1/U1  ( .A(b), .B(a), .Y(Result_mul) );
endmodule

