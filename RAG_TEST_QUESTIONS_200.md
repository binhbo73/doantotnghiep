# Bộ câu hỏi kiểm thử RAG nội bộ tối ưu theo intent và citation

Tạo ngày: 2026-06-05

Ghi chú: Bộ câu hỏi này được viết lại theo logic `query_intent.py`, `query_router.py` và `chat_service.py`. Câu hỏi ưu tiên có một chủ đề neo rõ, một loại yêu cầu rõ và hạn chế gom quá nhiều nguồn trong cùng một câu. Khi câu hỏi cần nhiều nguồn, yêu cầu hệ thống tách câu trả lời theo từng nhóm nguồn và chỉ trích dẫn nguồn chứa bằng chứng trực tiếp.

## A. Câu hỏi nghiệp vụ một nguồn hoặc một chủ đề rõ

1. Liệt kê các nội dung chính trong quy định về chất lượng, an toàn và KPI của công ty.
2. Trình bày cơ chế lương thưởng và KPI theo đúng các mục có trong tài liệu.
3. Ban Giám đốc có chức năng, nhiệm vụ và quyền hạn nào?
4. Phòng Hành chính Tổng hợp có chức năng và nhiệm vụ nào?
5. Phòng Kỹ thuật Kinh tế có những nhiệm vụ cụ thể nào?
6. Phòng Tài chính Kế toán có nhiệm vụ và trách nhiệm cụ thể gì?
7. Nguyên tắc tổ chức và điều hành của Ban Giám đốc được quy định như thế nào?
8. Liệt kê các mục về tổ chức và điều hành của Ban Giám đốc.
9. Quy định quản lý nhân sự gồm những nội dung chính nào?
10. Quy định về văn thư và lưu trữ gồm những trách nhiệm nào?
11. Quy trình quản lý dự án và tiến độ gồm các bước hoặc mốc nào?
12. Quy trình thanh toán và công nợ gồm các bước xử lý nào?
13. Quy định quản lý và sử dụng điện thoại gồm những yêu cầu chính nào?
14. Quy định kiểm tra và sử dụng điện yêu cầu những gì?
15. Quy định quản lý và sử dụng tài sản, công cụ nêu những trách nhiệm nào?
16. Việc mua và quản lý tài sản, công cụ được thực hiện theo nguyên tắc nào?
17. Việc sử dụng điện thoại trong nhóm tài sản, công cụ cần tuân thủ những gì?
18. Người đại diện có nhiệm vụ, trách nhiệm, quyền hạn và quyền lợi nào?
19. Cấp quản lý có nhiệm vụ, quyền hạn và trách nhiệm kiểm soát nào?
20. Quản trị viên tập sự cần đáp ứng điều kiện, nhiệm vụ và quyền lợi gì?
21. Chế độ báo cáo nội bộ yêu cầu những nội dung báo cáo nào?
22. Nguyên tắc phân công và lề lối làm việc trong cơ quan gồm những gì?
23. Công tác phối hợp quản lý trong công ty được quy định như thế nào?
24. Việc phân công trong nội bộ công ty gồm nguyên tắc và trách nhiệm nào?
25. Cán bộ nhân viên cần tuân thủ những quy định nào về lề lối làm việc?
26. Nội quy hội họp quy định những việc cần làm trước, trong và sau cuộc họp?
27. Ứng cử và tiến cử trong công ty có điều kiện và quy trình nào?
28. Quy định ra vào cổng áp dụng cho đối tượng nào và thủ tục ra sao?
29. Bản cam kết ra vào cổng gồm những nội dung cam kết nào?
30. Quy định bảo mật thông tin nêu mục đích, phạm vi và đối tượng áp dụng nào?
31. Quy định bảo mật thông tin liệt kê những loại thông tin cần bảo mật nào?
32. Tài khoản người dùng được cấp, sử dụng và bảo vệ theo trách nhiệm nào?
33. Việc lưu chuyển thông tin trong công ty được kiểm soát như thế nào?
34. Biện pháp phòng ngừa rủi ro bảo mật thông tin gồm những gì?
35. Khi sử dụng email công ty, nhân viên được phép và không được phép làm gì?
36. Việc sử dụng Internet trong công ty được quy định như thế nào?
37. Các nhóm kiểm soát an toàn bảo mật CNTT gồm những nhóm nào?
38. Mật khẩu cần được tạo, thay đổi và bảo vệ theo yêu cầu nào?
39. Truy cập từ xa cần điều kiện gì và người truy cập có trách nhiệm nào?
40. Quy định an toàn vệ sinh lao động gồm những yêu cầu chính nào?
41. Khi xảy ra tai nạn lao động, trình tự điều tra và khai báo là gì?
42. Kiểm tra an toàn, VSLĐ, PCCC và 5S gồm những tiêu chí nào?
43. Người lao động phải tuân thủ trách nhiệm gì về an toàn vệ sinh lao động?
44. Biên bản xử lý vi phạm kỷ luật cần có những trường thông tin nào?
45. Quyết định sa thải cần có căn cứ, nội dung và phần ký xác nhận nào?
46. Quyết định xử lý kỷ luật lao động gồm những mục và điều khoản nào?
47. Thông báo kỷ luật lao động cần thể hiện những thông tin nào?
48. Kỷ luật lao động gồm hành vi vi phạm, hình thức xử lý và nguyên tắc xử lý nào?
49. Quyết định đình chỉ công việc gồm những điều khoản chính nào?
50. Quyết định xử lý vi phạm kỷ luật lao động cần nêu những nội dung gì?
51. Quy trình tính lương gồm các bước tính, kiểm tra và phê duyệt nào?
52. Một quyết định ban hành chung thường gồm bố cục và điều khoản nào?
53. Quy định quản lý nhà ăn gồm phạm vi áp dụng, trách nhiệm và yêu cầu vận hành nào?
54. Hội đồng tuyển dụng gồm thành phần nào và có nhiệm vụ gì?
55. Tham gia hoạt động đào tạo có điều kiện, quyền lợi và trách nhiệm nào?
56. Nhân viên mới cần được hội nhập với những nội dung nào?
57. Quyết định bổ nhiệm giám đốc cần có căn cứ, nội dung bổ nhiệm và trách nhiệm nào?
58. Biên bản bàn giao mẫu 1 gồm những thông tin cần bàn giao nào?
59. Biên bản bàn giao mẫu 2 gồm những mục thông tin nào?
60. Biên bản họp Hội đồng quản trị hoặc Hội đồng thành viên gồm bố cục và nội dung nào?
61. Biên bản họp điều chuyển công việc cần ghi nhận những thông tin nào?
62. Quyết định bổ nhiệm gồm những căn cứ và điều khoản chính nào?
63. Thông báo điều chuyển công việc gồm những nội dung bắt buộc nào?
64. Quyết định điều chuyển công việc gồm những điều khoản nào?
65. Quyết định cử đi đào tạo gồm những nội dung gì?
66. Điều chuyển CBCNV không là cán bộ quản lý áp dụng điều kiện và quy trình nào?
67. Bổ nhiệm và điều chuyển nhân sự gồm các trường hợp, điều kiện và thẩm quyền nào?
68. Chế độ bàn giao của cán bộ nhân viên gồm những bước bàn giao nào?
69. Khi chuyển công tác, người lao động được hỗ trợ những khoản nào?
70. Việc quản lý và sử dụng máy fax có trách nhiệm và yêu cầu gì?
71. Việc quản lý và sử dụng máy tính mạng có những nguyên tắc nào?
72. Sử dụng ô tô cá nhân phục vụ công việc có điều kiện và chế độ thanh toán nào?
73. Quản lý và sử dụng phương tiện gồm những trách nhiệm nào?
74. Quy trình đề nghị, phê duyệt và điều xe được thực hiện như thế nào?
75. Việc mua, quản lý và sử dụng máy móc thiết bị gồm các bước nào?
76. Quản lý và sử dụng máy photocopy gồm những yêu cầu nào?
77. KPI và lương thưởng của Ban Giám đốc được xác định theo tiêu chí nào?
78. Bảng KPI, lương thưởng của Ban Giám đốc gồm những cột và chỉ tiêu nào?
79. Bảng theo dõi chỉnh sửa tài liệu gồm những trường dữ liệu nào?
80. Phí chức năng và phúc lợi nội bộ gồm những khoản nào?
81. Quy chế lương thưởng và chế độ cho người lao động gồm những chế độ nào?
82. Quyết định khen thưởng gồm căn cứ, đối tượng và hình thức khen thưởng nào?
83. Quy định mừng sinh nhật cho CBNV và khách hàng gồm những nội dung nào?
84. Quy định tổ chức sinh nhật CBNV gồm phạm vi, kinh phí và trách nhiệm nào?
85. Biên bản họp xét khen thưởng cần ghi nhận những nội dung nào?
86. Công tác phí và thanh toán chi phí công tác gồm khoản chi và điều kiện thanh toán nào?
87. Quyết định nâng lương gồm căn cứ và nội dung nâng lương nào?
88. Quyết định tăng lương gồm những điều khoản nào?
89. Đánh giá công việc nhân viên gồm tiêu chí và quy trình đánh giá nào?
90. Tiêu chí đánh giá công việc gồm những nhóm tiêu chí nào?
91. Biên bản họp hội đồng nâng lương gồm thành phần, nội dung họp và kết luận nào?
92. Mẫu bảng lương nội bộ gồm những cột dữ liệu nào? Trả lời bằng bảng markdown nếu nguồn có bảng.
93. Mẫu bảng KPI đánh giá nhân sự gồm các chỉ tiêu và cột nào? Trả lời bằng bảng markdown nếu nguồn có bảng.
94. Mẫu biên bản họp nội bộ gồm những phần thông tin nào?
95. Mẫu phiếu đề nghị thanh toán gồm những trường bắt buộc nào?
96. Thể thức trình bày văn bản Word quy định bố cục và định dạng như thế nào?

## B. Câu hỏi tổng hợp có phạm vi kiểm soát

97. Liệt kê các quy định liên quan đến bảo mật thông tin, tách câu trả lời theo từng nhóm nội dung: email, Internet, mật khẩu, tài khoản và truy cập từ xa.
98. So sánh quy định sử dụng email và quy định sử dụng Internet; chỉ nêu điểm giống, khác nếu có bằng chứng trong nguồn.
99. Liệt kê các chính sách CNTT liên quan đến email, Internet, mật khẩu, tài khoản người dùng và truy cập từ xa.
100. Liệt kê các nội dung liên quan đến lương, thưởng, nâng lương và KPI; tách theo từng nguồn hoặc từng biểu mẫu.
101. So sánh quy trình tính lương với quy chế lương thưởng cho người lao động; chỉ so sánh các mục có trong tài liệu.
102. Liệt kê các biểu mẫu liên quan đến thanh toán, bảng lương, KPI và biên bản họp; nêu mục đích từng biểu mẫu nếu nguồn có.
103. Liệt kê quy định và biểu mẫu liên quan trực tiếp đến xử lý kỷ luật lao động.
104. Tóm tắt theo từng nhóm: điều chuyển, bổ nhiệm, cử đi đào tạo và bàn giao công việc.
105. Liệt kê các quy định liên quan đến an toàn lao động, VSLĐ, PCCC và 5S; tách theo từng nội dung.
106. So sánh quy định quản lý tài sản với quy định sử dụng điện thoại, máy tính mạng, máy fax và máy photocopy.
107. Công ty quy định gì về công tác phí, thanh toán và công nợ? Tách theo từng quy trình hoặc biểu mẫu.
108. Tóm tắt quy định về hội họp, biên bản họp và họp xét khen thưởng; chỉ dùng nguồn liên quan trực tiếp.
109. Liệt kê các loại quyết định nội bộ có trong tài liệu và mục đích của từng loại.
110. Liệt kê chức năng chính của từng phòng ban theo các quy chế phòng ban.
111. Tóm tắt trách nhiệm chính của cấp quản lý theo đúng các mục trong tài liệu.
112. Liệt kê các quy định nhân sự theo chuỗi: tuyển dụng, hội nhập, đào tạo, đánh giá, khen thưởng, kỷ luật và lương.
113. Nhân viên mới vào công ty cần nắm những quy định nào? Sắp xếp theo nhóm nội dung, không suy luận ngoài tài liệu.
114. Nếu có tai nạn lao động, cần thực hiện những bước nào theo quy định về an toàn lao động?
115. Nếu cần xử lý vi phạm kỷ luật lao động, cần dùng quy định và biểu mẫu nào?
116. Nếu cần thanh toán công tác phí, cần chuẩn bị hồ sơ và tuân thủ quy định nào?
117. Nếu cần điều chuyển công việc cho nhân viên, cần thực hiện theo quy trình và biểu mẫu nào?
118. Nếu cần bảo vệ thông tin khách hàng và hợp đồng, quy định bảo mật thông tin nêu yêu cầu gì?
119. Liệt kê các bảng hoặc biểu mẫu có cột dữ liệu; trả lời bằng bảng markdown cho từng bảng có trong nguồn.
120. Liệt kê các quy định liên quan trực tiếp đến quyền lợi của người lao động; tách theo lương, phúc lợi, đào tạo, công tác phí và chuyển công tác.

## C. Câu hỏi hỏi sâu, tình huống và đối chiếu

121. Liệt kê đầy đủ các loại thông tin phải bảo mật theo quy định bảo mật thông tin.
122. Cá nhân hoặc bộ phận phải chịu trách nhiệm gì khi để lộ thông tin theo quy định bảo mật?
123. Email công ty có được dùng để trao đổi thông tin nội bộ và thông tin khách hàng không? Nêu điều kiện được phép và các hạn chế nếu tài liệu có.
124. Mật khẩu phải được tạo, lưu giữ và thay đổi như thế nào theo quy định bảo mật CNTT?
125. Việc cấp, thu hồi và quản lý tài khoản người dùng được thực hiện như thế nào?
126. Ai được phép truy cập từ xa và cần đáp ứng điều kiện gì?
127. Khi sử dụng Internet, những hành vi nào bị cấm hoặc bị hạn chế?
128. Quy định bảo mật mạng LAN, máy chủ hoặc hệ thống nội bộ gồm những yêu cầu nào?
129. Nếu nhân viên gửi tài liệu khách hàng ra ngoài bằng email cá nhân, quy định bảo mật nào được áp dụng?
130. Nếu nhân viên quên khóa máy tính hoặc để lộ mật khẩu, tài liệu có căn cứ xử lý hoặc yêu cầu khắc phục nào?
131. Thành phần thu nhập hoặc chế độ của người lao động gồm những gì theo quy chế lương thưởng?
132. Dữ liệu đầu vào để tính lương gồm những gì theo quy trình tính lương?
133. Các bộ phận có trách nhiệm gì trong quá trình tính lương?
134. Nâng lương và tăng lương được thể hiện khác nhau như thế nào trong các biểu mẫu quyết định?
135. Họp hội đồng nâng lương cần có nội dung nào để làm căn cứ quyết định?
136. Các tiêu chí đánh giá công việc nhân viên là gì?
137. Đánh giá công việc có thang điểm, xếp loại hoặc cách tổng hợp kết quả không? Chỉ trả lời phần có trong tài liệu.
138. Bảng lương nội bộ gồm những cột nào và ý nghĩa từng cột nếu nguồn có mô tả?
139. Bảng KPI đánh giá nhân sự gồm chỉ tiêu nào và cách ghi nhận ra sao?
140. KPI trong quy chế lương thưởng và KPI trong bảng đánh giá nhân sự giống và khác nhau ở điểm nào?
141. Những khoản chi phí công tác nào được thanh toán?
142. Thanh toán công tác phí cần điều kiện, chứng từ và phê duyệt nào?
143. Phiếu đề nghị thanh toán cần điền những thông tin nào?
144. Các bước kiểm tra chứng từ thanh toán và công nợ là gì?
145. Nhân viên đi công tác phát sinh chi phí cần làm gì từ lúc đề nghị đến lúc thanh toán?
146. Nếu chứng từ thanh toán thiếu thông tin, trách nhiệm kiểm tra và xử lý thuộc về ai?
147. Đơn vị quản lý nhà ăn và người sử dụng nhà ăn có trách nhiệm gì?
148. Sử dụng điện thoại có định mức hoặc nguyên tắc kiểm soát nào?
149. Kiểm tra và sử dụng điện cần tuân thủ yêu cầu an toàn nào?
150. Sử dụng máy tính mạng có những hành vi nào bị hạn chế?
151. Người dùng máy fax phải bảo quản và sử dụng như thế nào?
152. Máy photocopy được sử dụng, bảo trì và kiểm soát ra sao?
153. Sử dụng ô tô cá nhân để phục vụ công việc được hỗ trợ trong điều kiện nào?
154. Quy trình điều xe từ đề nghị đến xét duyệt và sử dụng là gì?
155. Người được giao phương tiện có trách nhiệm gì?
156. Quy trình mua sắm và quản lý máy móc thiết bị gồm những bước nào?
157. Nguyên tắc phối hợp giữa cá nhân và bộ phận trong công ty là gì?
158. Cơ chế phối hợp, báo cáo và xử lý công việc được quy định ra sao?
159. Nguyên tắc giao việc và chịu trách nhiệm trong nội bộ công ty là gì?
160. Người đại diện có những quyền lợi nào?
161. Cấp quản lý có quyền quyết định và trách nhiệm kiểm soát gì?
162. Quản trị viên tập sự được giao mục tiêu, nhiệm vụ và đánh giá kết quả ra sao?
163. Báo cáo nội bộ phải thực hiện theo kỳ hạn, nội dung và người nhận nào?
164. Nếu một phòng ban không phối hợp đúng hạn, tài liệu quy định cách xác định trách nhiệm như thế nào?
165. Ai chịu trách nhiệm chuẩn bị tài liệu, tham dự và ghi biên bản họp?
166. Biên bản họp nội bộ gồm những trường thông tin nào và dùng trong trường hợp nào?
167. Biên bản họp Hội đồng quản trị khác biên bản họp nội bộ ở điểm nào?
168. Biên bản họp xét khen thưởng cần thể hiện căn cứ, ý kiến và kết luận như thế nào?
169. Khen thưởng được quyết định theo đối tượng, hình thức và hiệu lực ra sao?
170. Tổ chức sinh nhật CBNV và mừng sinh nhật khách hàng khác nhau ở điểm nào?
171. Người được cử đi đào tạo có quyền lợi và nghĩa vụ gì?
172. Quyết định cử đi đào tạo cần có những thông tin bắt buộc nào?
173. Nhân viên mới cần được phổ biến những nội dung nào khi hội nhập?
174. Hội đồng tuyển dụng gồm thành phần nào và có nhiệm vụ gì?
175. Bổ nhiệm thông thường và bổ nhiệm giám đốc khác nhau ở điểm nào?
176. Bổ nhiệm và điều chuyển cần điều kiện, thẩm quyền và quy trình ra sao?
177. Thông báo điều chuyển công việc cần gửi những thông tin nào cho người lao động?
178. Quyết định điều chuyển công việc cần nêu điều khoản và trách nhiệm thi hành nào?
179. Điều chuyển CBCNV không là cán bộ quản lý áp dụng trong trường hợp nào?
180. Chuyển công tác được hỗ trợ theo đối tượng, điều kiện và khoản hỗ trợ nào?
181. Quy trình bàn giao của cán bộ nhân viên gồm từng bước nào?
182. Biên bản bàn giao mẫu 1 và mẫu 2 giống và khác nhau ở điểm nào?
183. Khi nhân viên nghỉ việc hoặc chuyển vị trí, cần bàn giao theo quy định nào?
184. Có những hình thức xử lý kỷ luật lao động nào?
185. Nguyên tắc, thẩm quyền và trình tự xử lý kỷ luật lao động là gì?
186. Biên bản xử lý vi phạm kỷ luật cần ghi nhận sự việc, ý kiến và kết luận như thế nào?
187. Thông báo kỷ luật lao động cần gửi cho ai và gồm nội dung gì?
188. Quyết định xử lý kỷ luật lao động cần có căn cứ và hình thức xử lý nào?
189. Quyết định sa thải cần có những phần nào trước khi ban hành?
190. Đình chỉ công việc được dùng trong trường hợp nào và cần ghi rõ điều gì?
191. Quyết định xử lý vi phạm kỷ luật lao động có hiệu lực và trách nhiệm thi hành ra sao?
192. Nếu một nhân viên vi phạm nội quy hội họp nhiều lần, tài liệu có nêu hướng xử lý hoặc căn cứ liên quan nào không?
193. Người lao động và người quản lý có trách nhiệm gì về an toàn vệ sinh lao động?
194. Trình tự báo cáo tai nạn lao động từ lúc phát hiện đến khi xử lý là gì?
195. Kiểm tra an toàn, VSLĐ, PCCC và 5S định kỳ gồm những nội dung nào?
196. Nếu xảy ra tai nạn lao động trong khu vực sản xuất, cần xử lý và lập hồ sơ như thế nào?
197. Trích xuất nguyên bảng liên quan đến câu hỏi hiện tại nếu nguồn có bảng; giữ đúng tên cột và hàng dữ liệu.
198. Liệt kê các biểu mẫu nội bộ và nêu mục đích sử dụng từng biểu mẫu theo từng nguồn.
199. Khi hỏi một mục hoặc quy định cần đầy đủ, hệ thống đã lấy được mục chính, mục con và chi tiết liên quan chưa?
200. Tạo checklist kiểm thử RAG gồm: đúng nguồn, đủ nội dung, giữ bảng/biểu mẫu, citation đúng và xử lý khi không có thông tin.

## D. Câu hỏi kiểm thử sai phạm vi quyền/phòng ban

Mục tiêu: người dùng vẫn hỏi tự nhiên, không biết file/folder. Người kiểm thử chỉ thay đổi quyền hoặc phạm vi truy cập phía sau. Nếu quyền/phạm vi không có nguồn phù hợp, hệ thống phải nói rõ không có thông tin trong phạm vi được phép truy cập, không được lấy nguồn từ phòng ban khác.

N1. Thiết lập user chỉ có quyền nhóm tài chính kế toán. Câu hỏi: Quy định bảo mật thông tin liệt kê những loại thông tin nào cần bảo mật?
Kỳ vọng: Không lấy nguồn từ nhóm bảo mật nếu user không có quyền nguồn đó.

N2. Thiết lập user chỉ có quyền nhóm bảo mật thông tin. Câu hỏi: Quy trình tính lương gồm những bước nào?
Kỳ vọng: Không lấy nguồn từ nhóm lương/phúc lợi.

N3. Thiết lập user chỉ có quyền nhóm hậu cần, xe, thiết bị. Câu hỏi: Quy chế lương thưởng và chế độ cho người lao động gồm những chế độ nào?
Kỳ vọng: Không trả lời bằng quy chế lương thưởng nếu không có trong phạm vi quyền.

N4. Thiết lập user chỉ có quyền nhóm phúc lợi, khen thưởng. Câu hỏi: Kiểm tra an toàn, VSLĐ, PCCC và 5S gồm những tiêu chí nào?
Kỳ vọng: Không lấy nguồn từ nhóm an toàn lao động.

N5. Thiết lập user chỉ có quyền nhóm kỷ luật lao động. Câu hỏi: Mẫu phiếu đề nghị thanh toán gồm những trường bắt buộc nào?
Kỳ vọng: Không lấy nguồn từ mẫu biểu chung hoặc kế toán.

N6. Thiết lập user chỉ có quyền nhóm mẫu biểu chung. Câu hỏi: Kỷ luật lao động gồm những hình thức xử lý nào?
Kỳ vọng: Không trả lời bằng quy định kỷ luật nếu user không có quyền nguồn đó.

N7. Thiết lập user chỉ có quyền nhóm tuyển dụng, bổ nhiệm, điều chuyển. Câu hỏi: Mật khẩu phải đáp ứng yêu cầu gì theo quy định bảo mật CNTT?
Kỳ vọng: Không lấy nguồn từ nhóm bảo mật thông tin.

N8. Thiết lập user chỉ có quyền nhóm quy chế phòng ban. Câu hỏi: Biên bản bàn giao mẫu 1 gồm những thông tin cần bàn giao nào?
Kỳ vọng: Không lấy nguồn từ nhóm bàn giao nếu không nằm trong phạm vi quyền.

N9. Thiết lập user chỉ có quyền nhóm quản lý tài sản, công cụ. Câu hỏi: Quyết định nâng lương gồm căn cứ và nội dung nâng lương nào?
Kỳ vọng: Không lấy nguồn từ nhóm thưởng/nâng lương.

N10. Thiết lập user chỉ có quyền nhóm thưởng, nâng lương. Câu hỏi: Quản lý và sử dụng máy photocopy gồm những yêu cầu nào?
Kỳ vọng: Không lấy nguồn từ nhóm hậu cần/tài sản.

N11. Thiết lập user chỉ có quyền nhóm an toàn lao động. Câu hỏi: Nội quy hội họp quy định những việc cần làm trước, trong và sau cuộc họp?
Kỳ vọng: Không lấy nguồn từ nhóm nội quy hội họp.

N12. Thiết lập user chỉ có quyền nhóm nội quy. Câu hỏi: Trình tự điều tra và khai báo tai nạn lao động là gì?
Kỳ vọng: Không lấy nguồn từ nhóm an toàn lao động.

N13. Thiết lập user chỉ có quyền nhóm quản lý nhà ăn. Câu hỏi: Hội đồng tuyển dụng gồm thành phần nào và có nhiệm vụ gì?
Kỳ vọng: Không lấy nguồn từ nhóm tuyển dụng.

N14. Thiết lập user chỉ có quyền nhóm lương, phúc lợi. Câu hỏi: Việc lưu chuyển thông tin được kiểm soát như thế nào?
Kỳ vọng: Không lấy nguồn từ nhóm bảo mật thông tin.
