// Broken 4-bit parity circuit for demonstration.
// Error: U4 and U5 create dead_branch_1, but that branch never affects the parity output.
module four_bit_parity_wrong_dead_logic (a, parity);
  input [3:0] a;
  output parity;
  wire xor_low, xor_high, dead_branch_0, dead_branch_1;

  XOR2_X1M_A9TH U1 (.A(a[0]), .B(a[1]), .Y(xor_low));
  XOR2_X1M_A9TH U2 (.A(a[2]), .B(a[3]), .Y(xor_high));
  XOR2_X1M_A9TH U3 (.A(xor_low), .B(xor_high), .Y(parity));

  // This branch is disconnected from parity: it wastes logic and may be a missed wire.
  XOR2_X1M_A9TH U4 (.A(a[0]), .B(a[3]), .Y(dead_branch_0));
  INV_X1M_A9TH  U5 (.A(dead_branch_0), .Y(dead_branch_1));
endmodule
