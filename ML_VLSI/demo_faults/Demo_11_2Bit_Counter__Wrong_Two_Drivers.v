// Broken 2-bit counter for demonstration.
// Error: U2 (XOR) and U5 (BUF) both drive next_count1, the D input of the count[1] flip-flop.
module two_bit_counter_wrong_two_drivers (clk, count);
  input clk;
  output [1:0] count;
  wire next_count0, next_count1;

  INV_X1M_A9TH  U1 (.A(count[0]), .Y(next_count0));
  XOR2_X1M_A9TH U2 (.A(count[1]), .B(count[0]), .Y(next_count1));
  DFFQ_X1       U3 (.D(next_count0), .CK(clk), .Q(count[0]));
  DFFQ_X1       U4 (.D(next_count1), .CK(clk), .Q(count[1]));
  BUF_X1M_A9TH  U5 (.A(count[0]), .Y(next_count1));
endmodule
