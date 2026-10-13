// Correct 2-bit ripple-carry adder.
// sum = a + b + cin; carry0 connects the least-significant stage to the most-significant stage.
module two_bit_adder_correct (a, b, cin, sum, cout);
  input [1:0] a, b;
  input cin;
  output [1:0] sum;
  output cout;
  wire carry0;

  ADDF_X1M_A9TH U1 (.A(a[0]), .B(b[0]), .CI(cin),    .S(sum[0]), .CO(carry0));
  ADDF_X1M_A9TH U2 (.A(a[1]), .B(b[1]), .CI(carry0), .S(sum[1]), .CO(cout));
endmodule
