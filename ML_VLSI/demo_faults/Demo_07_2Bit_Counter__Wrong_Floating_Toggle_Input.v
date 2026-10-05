// Broken 2-bit counter for demonstration.
// Error: U2 should use count[0] to decide when bit 1 toggles, but it reads missing_toggle instead.
module two_bit_counter_wrong_floating_toggle (clk, count);
  input clk;
  output [1:0] count;
  wire next_count0, next_count1, missing_toggle;

  INV_X1M_A9TH  U1 (.A(count[0]), .Y(next_count0));
  XOR2_X1M_A9TH U2 (.A(count[1]), .B(missing_toggle), .Y(next_count1));
  DFFQ_X1       U3 (.D(next_count0), .CK(clk), .Q(count[0]));
  DFFQ_X1       U4 (.D(next_count1), .CK(clk), .Q(count[1]));
endmodule
