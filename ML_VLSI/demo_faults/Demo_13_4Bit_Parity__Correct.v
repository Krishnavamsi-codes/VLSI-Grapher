// Correct 4-bit even-parity generator: parity = a[0] XOR a[1] XOR a[2] XOR a[3].
module four_bit_parity_correct (a, parity);
  input [3:0] a;
  output parity;
  wire xor_low, xor_high;

  XOR2_X1M_A9TH U1 (.A(a[0]), .B(a[1]), .Y(xor_low));
  XOR2_X1M_A9TH U2 (.A(a[2]), .B(a[3]), .Y(xor_high));
  XOR2_X1M_A9TH U3 (.A(xor_low), .B(xor_high), .Y(parity));
endmodule
